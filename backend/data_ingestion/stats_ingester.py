"""
Production-ready data ingestion for player career statistics.

Fetches all players from the database, calls the ATP stats API for each,
and upserts the aggregated career stats into the player_stats table.

Key features:
- Idempotent upserts using ON CONFLICT (player_id, stat_type) DO UPDATE
- Exponential backoff retry logic for API failures (429, timeout)
- Rate limiting (1.5s delay between requests)
- Batch processing to avoid memory overhead
- Comprehensive logging and error handling
- Field mapping from API response to database schema
- Unmapped fields stored in vendor_stats JSONB column
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# API Configuration
API_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"
API_BASE_URL = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/atp/h2h"
REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 5.0  # seconds between requests (increased further to handle stricter rate limiting)
MAX_RETRIES = 5
RETRY_BASE_DELAY = 5  # seconds (exponential backoff: 5, 10, 20, 40, 80)

# Field mapping: API response field -> database column name
# Only the 8 columns in player_stats table that have direct equivalents
FIELD_MAPPING_TO_COLUMNS = {
    "aces": "aces",
    "doubleFaults": "double_faults",
    "firstServePercentage": "first_serve_pct",
    "winningOnFirstServePercentage": "first_serve_win_pct",
    "winningOnSecondServePercentage": "second_serve_win_pct",
    "returnPtsWinPercentage": "return_points_won_pct",
    "breakpointsWonPercentage": "break_points_converted_pct",
    "tiebreakWon": "tiebreaks_won_pct",  # Note: This is count, will store as percentage in extra_stats
}

# All 50+ fields from API (including those stored in extra_stats)
ALL_API_FIELDS = {
    # Basic match stats
    "statMatchesPlayed", "matchesWon",
    
    # Aces and errors
    "aces", "doubleFaults", "unforcedErrors", "winners",
    
    # First serve stats
    "firstServe", "firstServeOf", "firstServePercentage",
    "winningOnFirstServe", "winningOnFirstServeOf", "winningOnFirstServePercentage",
    "averageFirstServeSpeed",
    
    # Second serve stats
    "winningOnSecondServe", "winningOnSecondServeOf", "winningOnSecondServePercentage",
    "averageSecondServeSpeed",
    
    # Serve speed
    "fastestServe", "averageFastestServe",
    
    # Break point stats
    "breakPointsConverted", "breakPointsConvertedOf", "breakpointsWonPercentage",
    
    # Net approaches
    "netApproaches", "netApproachesOf",
    
    # Return stats
    "returnPtsWin", "returnPtsWinOf", "returnPtsWinPercentage",
    
    # Total points
    "totalPointsWon",
    
    # Sets and games
    "setsWon", "gamesWon",
    
    # Best of three (most common)
    "bestOfThreeWon", "bestOfThreeCount", "bestOfThreeWonPercentage",
    
    # Best of five (Grand Slams)
    "bestOfFiveWon", "bestOfFiveCount", "bestOfFiveWonPercentage",
    
    # First set correlation
    "firstSetWinMatchWin", "firstSetWinMatchWinPercentage",
    "firstSetWinMatchLose", "firstSetWinMatchLosePercentage",
    "firstSetLoseMatchWin", "firstSetLoseMatchWinPercentage",
    "firstSetWinCount", "firstSetLoseCount",
    
    # Deciding set stats
    "decidingSetWin", "decidingSetCount", "decidingSetWinPercentage",
    
    # Tiebreak stats
    "tiebreakWon", "tiebreakCount", "totalTBWinPercentage",
    
    # Tournament breakdown
    "title", "grandSlam", "masters", "mainTour", "tourFinals", "cups", "futures", "challengers",
    
    # Surface breakdown
    "hard", "clay", "iHard", "grass",
}


def fetch_players(session: Session, limit: Optional[int] = None) -> List[Tuple[int, str]]:
    """
    Fetch all players from the database with pagination.
    
    Args:
        session: SQLAlchemy session
        limit: Optional limit for testing
        
    Returns:
        List of tuples (player_id, player_name)
    """
    query = "SELECT id, full_name FROM players ORDER BY id"
    if limit:
        query += f" LIMIT {limit}"
    
    rows = session.execute(text(query)).fetchall()
    return [(row[0], row[1]) for row in rows]


def fetch_player_stats(
    player_id: int,
    api_key: str,
    retries: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Fetch player stats from ATP API with exponential backoff retry logic.
    
    Args:
        player_id: ATP player ID
        api_key: RapidAPI key from environment
        retries: Current retry attempt count
        
    Returns:
        Parsed JSON response (data.playerStats) or None on failure
    """
    if retries > 0:
        delay = RETRY_BASE_DELAY * (2 ** (retries - 1))
        logger.warning(f"Retrying player {player_id}, attempt {retries}/{MAX_RETRIES}, waiting {delay}s...")
        time.sleep(delay)
    
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": api_key,
    }
    
    url = f"{API_BASE_URL}/vs-all-stats/{player_id}/"
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        # Handle rate limiting
        if response.status_code == 429:
            if retries < MAX_RETRIES:
                return fetch_player_stats(player_id, api_key, retries + 1)
            else:
                logger.error(f"Player {player_id}: Rate limited after {MAX_RETRIES} retries")
                return None
        
        response.raise_for_status()
        
        data = response.json()
        player_stats = data.get("data", {}).get("playerStats")
        
        if not player_stats:
            logger.warning(f"Player {player_id}: No playerStats in response")
            return None
        
        return player_stats
        
    except requests.exceptions.Timeout:
        if retries < MAX_RETRIES:
            logger.warning(f"Player {player_id}: Request timeout, retrying...")
            return fetch_player_stats(player_id, api_key, retries + 1)
        else:
            logger.error(f"Player {player_id}: Timeout after {MAX_RETRIES} retries")
            return None
            
    except requests.exceptions.RequestException as e:
        if retries < MAX_RETRIES and isinstance(e, requests.exceptions.ConnectionError):
            logger.warning(f"Player {player_id}: Connection error, retrying...")
            return fetch_player_stats(player_id, api_key, retries + 1)
        else:
            logger.error(f"Player {player_id}: API request failed: {e}")
            return None


def transform_response(api_response: Dict[str, Any], player_id: int) -> Dict[str, Any]:
    """
    Transform API response into database schema format.
    
    Maps:
    - Known API fields to the 8 main player_stats columns
    - All 50+ stats fields to extra_stats JSONB for full preservation
    - Sets period='career' for all rows
    - Handles missing/null fields gracefully
    
    Args:
        api_response: playerStats object from API
        player_id: ATP player ID
        
    Returns:
        Dictionary keyed by database column names with values
    """
    transformed = {
        "player_id": player_id,
        "period": "career",  # All stats are career aggregates
        "match_id": None,  # No specific match, aggregate stats
        "surface": None,  # No surface filter in this aggregation
    }
    
    # Map the 8 main stat columns
    for api_field, db_column in FIELD_MAPPING_TO_COLUMNS.items():
        value = api_response.get(api_field)
        
        if value is None or value == "":
            transformed[db_column] = None
        else:
            try:
                # Convert to appropriate numeric type
                if isinstance(value, str):
                    if "." in str(value):
                        transformed[db_column] = float(value)
                    else:
                        transformed[db_column] = int(value)
                else:
                    transformed[db_column] = value
            except (ValueError, TypeError):
                transformed[db_column] = None
    
    # Store all raw API stats in extra_stats JSONB for full preservation
    extra_stats = {}
    for api_field in ALL_API_FIELDS:
        value = api_response.get(api_field)
        if value is not None and value != "":
            try:
                # Convert string numbers to actual numbers
                if isinstance(value, str):
                    if "." in str(value):
                        extra_stats[api_field] = float(value)
                    else:
                        extra_stats[api_field] = int(value)
                else:
                    extra_stats[api_field] = value
            except (ValueError, TypeError):
                extra_stats[api_field] = value
    
    transformed["extra_stats"] = json.dumps(extra_stats) if extra_stats else None
    
    return transformed


def upsert_player_stats(session: Session, batch_data: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """
    Batch upsert player stats.
    
    Since the table doesn't have a unique constraint on (player_id, period),
    we delete existing 'career' stats for these players, then insert new ones.
    This ensures idempotency: re-running the script won't create duplicates.
    
    Args:
        session: SQLAlchemy session
        batch_data: List of dictionaries with transformed player stats
        
    Returns:
        Tuple of (rows_affected, list of errors)
    """
    if not batch_data:
        return 0, []
    
    errors = []
    
    try:
        # Extract player_ids to delete existing career stats
        player_ids = [row["player_id"] for row in batch_data]
        player_ids_str = ", ".join(str(pid) for pid in player_ids)
        
        # Delete existing 'career' stats for these players (idempotency)
        delete_sql = f"""
            DELETE FROM player_stats
            WHERE player_id IN ({player_ids_str})
            AND period = 'career'
        """
        session.execute(text(delete_sql))
        
        # Get column names from first row
        columns = list(batch_data[0].keys())
        columns_str = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])
        
        # Insert new stats
        insert_sql = f"""
            INSERT INTO player_stats ({columns_str})
            VALUES ({placeholders})
        """
        
        result = session.execute(text(insert_sql), [dict(row) for row in batch_data])
        session.commit()
        return result.rowcount, errors
    except Exception as e:
        session.rollback()
        errors.append(str(e))
        logger.error(f"Upsert batch failed: {e}")
        return 0, errors


def ingest_player_stats(
    session: Session,
    api_key: str,
    batch_size: int = 50,
    player_ids: Optional[List[int]] = None,
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Main ingestion orchestration function.
    
    Args:
        session: SQLAlchemy session
        api_key: RapidAPI key
        batch_size: Number of players to process before batch upsert
        player_ids: Optional list of specific player IDs to ingest (for testing)
        dry_run: If True, only fetch and transform, don't insert
        
    Returns:
        Dictionary with success_count, failure_count, skipped_count
    """
    # Fetch players
    if player_ids:
        players = [(pid, f"Player {pid}") for pid in player_ids]
        logger.info(f"Ingesting {len(players)} specific players (dry_run={dry_run})")
    else:
        players = fetch_players(session)
        logger.info(f"Ingesting {len(players)} total players (dry_run={dry_run})")
    
    success_count = 0
    failure_count = 0
    skipped_count = 0
    batch = []
    
    for idx, (player_id, player_name) in enumerate(players, 1):
        # Fetch stats from API
        api_response = fetch_player_stats(player_id, api_key)
        
        if api_response is None:
            failure_count += 1
            continue
        
        # Transform response
        try:
            transformed = transform_response(api_response, player_id)
            batch.append(transformed)
        except Exception as e:
            logger.error(f"Transform failed for player {player_id}: {e}")
            failure_count += 1
            continue
        
        # Log progress every batch_size players
        if idx % batch_size == 0 or idx == len(players):
            logger.info(f"Processed {idx}/{len(players)} players")
        
        # Upsert batch when full
        if len(batch) >= batch_size:
            if not dry_run:
                inserted, errors = upsert_player_stats(session, batch)
                success_count += inserted
                if errors:
                    failure_count += len(errors)
            else:
                success_count += len(batch)
                logger.debug(f"[DRY RUN] Would upsert {len(batch)} records")
            
            batch = []
        
        # Rate limiting between requests
        time.sleep(RATE_LIMIT_DELAY)
    
    # Upsert final batch
    if batch:
        if not dry_run:
            inserted, errors = upsert_player_stats(session, batch)
            success_count += inserted
            if errors:
                failure_count += len(errors)
        else:
            success_count += len(batch)
            logger.debug(f"[DRY RUN] Would upsert final {len(batch)} records")
    
    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "skipped_count": skipped_count,
        "total_players": len(players),
    }
