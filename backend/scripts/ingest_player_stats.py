#!/usr/bin/env python3
"""
CLI entry point for player stats data ingestion.

Usage:
    python ingest_player_stats.py                    # Ingest all players
    python ingest_player_stats.py --batch-size 100   # Custom batch size
    python ingest_player_stats.py --dry-run          # Test without writing
    python ingest_player_stats.py --player-ids 47275,68074  # Test specific players
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db import SessionLocal, engine
from data_ingestion.stats_ingester import ingest_player_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for stats ingestion CLI."""
    parser = argparse.ArgumentParser(
        description="Ingest ATP player career stats from RapidAPI into player_stats table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest all players with default batch size (50)
  python ingest_player_stats.py

  # Use custom batch size
  python ingest_player_stats.py --batch-size 100

  # Dry run (fetch and transform, no database writes)
  python ingest_player_stats.py --dry-run

  # Test with specific players
  python ingest_player_stats.py --player-ids 47275,68074,3320

  # Combine flags
  python ingest_player_stats.py --player-ids 47275 --dry-run
        """,
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of players to process before batch upsert (default: 50)",
    )
    
    parser.add_argument(
        "--player-ids",
        type=str,
        help="Comma-separated list of player IDs to ingest (for testing)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and transform data, but don't write to database",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate batch size
    if args.batch_size < 1:
        logger.error("--batch-size must be >= 1")
        return 1
    
    # Parse player IDs if provided
    player_ids = None
    if args.player_ids:
        try:
            player_ids = [int(pid.strip()) for pid in args.player_ids.split(",")]
            logger.info(f"Testing with {len(player_ids)} specific players: {player_ids}")
        except ValueError:
            logger.error(f"Invalid --player-ids format. Expected comma-separated integers, got: {args.player_ids}")
            return 1
    
    # Load configuration
    try:
        settings = get_settings()
        if not settings.tennis_api_key:
            logger.error("TENNIS_API_KEY environment variable not set")
            return 1
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return 1
    
    # Verify database connection
    try:
        with engine.connect() as conn:
            logger.info("✓ Database connection verified")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return 1
    
    # Run ingestion
    try:
        session = SessionLocal()
        
        logger.info("=" * 80)
        logger.info(f"Starting player stats ingestion")
        logger.info(f"  Batch size: {args.batch_size}")
        logger.info(f"  Dry run: {args.dry_run}")
        logger.info(f"  Specific players: {'Yes' if player_ids else 'No'}")
        logger.info("=" * 80)
        
        results = ingest_player_stats(
            session=session,
            api_key=settings.tennis_api_key,
            batch_size=args.batch_size,
            player_ids=player_ids,
            dry_run=args.dry_run,
        )
        
        logger.info("=" * 80)
        logger.info("INGESTION COMPLETE")
        logger.info(f"  Total players processed: {results['total_players']}")
        logger.info(f"  ✓ Successful upserts: {results['success_count']}")
        logger.info(f"  ✗ Failures: {results['failure_count']}")
        logger.info(f"  ⊘ Skipped: {results['skipped_count']}")
        
        if args.dry_run:
            logger.info("  (DRY RUN - no database writes)")
        
        logger.info("=" * 80)
        
        session.close()
        
        # Exit with error if there were failures
        if results['failure_count'] > 0:
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nIngestion cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Ingestion failed with exception: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
