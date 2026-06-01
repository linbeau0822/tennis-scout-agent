"""
Daily database update script for tennis-scout-agent.

Fetches fresh data from the ATP API and upserts into PostgreSQL. Safe to run
multiple times — all writes are idempotent. Designed to be run as a scheduled
cron job once per day.

Usage:
    .venv/bin/python data/daily_update.py [options]

Steps (all run by default):
    1. Rankings  — update players.current_ranking from ATP rankings endpoint
    2. Matches   — fetch recent matches (last --lookback-days days) and upsert
    3. Tournaments — fill in metadata for stub tournament rows
    4. Stats     — refresh career aggregate stats for all ranked players
    5. H2H       — recompute head_to_head win counts from match data in DB
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

# Ensure CWD is project root before any imports that trigger get_settings(),
# since pydantic-settings resolves env_file=".env" relative to CWD.
import os as _os
_os.chdir(str(PROJECT_ROOT))

for _p in (str(BACKEND_ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# seed_data adds BACKEND_ROOT to sys.path at import time, so these must come after
from seed_data import (  # noqa: E402
    ROUND_MAP,
    _PER_MATCH_STAT_KEYS_PLAYER1,
    _PER_MATCH_STAT_KEYS_PLAYER2,
    _extract_match_surface,
    _extract_per_match_stats,
    backfill_tournaments,
    engine as sd_engine,
    sync_top200_rankings,
)
from data_ingestion.stats_ingester import ingest_player_stats  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.atp_api_service import fetch_player_matches  # noqa: E402
from sqlalchemy import text  # noqa: E402

logger = logging.getLogger("daily_update")

BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _parse_match_date(raw_date: str | None) -> date | None:
    if not raw_date:
        return None
    try:
        return date.fromisoformat(str(raw_date)[:10])
    except (ValueError, TypeError):
        return None


def fetch_recent_matches(
    engine,
    lookback_days: int = 30,
    dry_run: bool = False,
) -> dict:
    """
    Fetch matches played in the last `lookback_days` days for all ranked players
    and upsert into the DB. Pages through the ATP API newest-first and stops
    early once matches are older than the cutoff.

    Returns a dict with counts: matches_upserted, new_players, tournament_stubs.
    """
    cutoff = date.today() - timedelta(days=lookback_days)
    logger.info("Fetching matches since %s (cutoff: %s days ago)", cutoff, lookback_days)

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT id, full_name FROM players "
                "WHERE current_ranking IS NOT NULL "
                "ORDER BY current_ranking"
            )
        ).fetchall()

    total_players = len(rows)
    logger.info("Processing %d ranked players", total_players)

    all_matches: dict[int, dict] = {}
    all_player_refs: dict[int, dict] = {}
    all_tournament_ids: set[int] = set()

    for idx, (player_id, player_name) in enumerate(rows, 1):
        page_no = 1
        player_match_count = 0
        try:
            while True:
                page = fetch_player_matches(
                    player_id, page_size=100, page_no=page_no, delay=1.5
                )
                if not page:
                    break

                hit_cutoff = False
                for m in page:
                    match_date = _parse_match_date(m.get("date"))
                    if match_date is not None and match_date < cutoff:
                        hit_cutoff = True
                        break

                    mid = int(m["id"])
                    if mid not in all_matches:
                        all_matches[mid] = m
                        player_match_count += 1

                    for pkey in ("player1", "player2"):
                        p = m.get(pkey, {})
                        pid = p.get("id")
                        if pid and pid not in all_player_refs:
                            all_player_refs[pid] = p

                    tid = m.get("tournamentId")
                    if tid:
                        all_tournament_ids.add(tid)

                if hit_cutoff or len(page) < 100:
                    break
                page_no += 1

            logger.debug(
                "[%d/%d] %s — %d recent match(es) collected",
                idx, total_players, player_name, player_match_count,
            )
        except Exception as exc:
            logger.warning("[%d/%d] %s — ERROR: %s", idx, total_players, player_name, exc)

    logger.info("Collected %d unique recent matches", len(all_matches))

    if dry_run:
        logger.info(
            "[DRY RUN] Would upsert %d matches, %d player refs, %d tournament stubs",
            len(all_matches), len(all_player_refs), len(all_tournament_ids),
        )
        return {"matches_upserted": 0, "new_players": 0, "tournament_stubs": 0}

    if not all_matches:
        return {"matches_upserted": 0, "new_players": 0, "tournament_stubs": 0}

    # Insert unknown opponent players
    with engine.begin() as conn:
        existing_ids = {r[0] for r in conn.execute(text("SELECT id FROM players")).fetchall()}
        existing_names = {
            r[0].lower() for r in conn.execute(text("SELECT full_name FROM players")).fetchall()
        }

    new_players = []
    seen_names: set[str] = set()
    for pid, pdata in all_player_refs.items():
        if pid in existing_ids:
            continue
        name = pdata.get("name") or f"Unknown Player {pid}"
        if name.strip().lower() in ("unknown", "unknown player", ""):
            name = f"Unknown Player {pid}"
        if name.lower() in existing_names or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        parts = name.split(" ", 1)
        new_players.append({
            "id": pid,
            "first_name": parts[0],
            "last_name": parts[1] if len(parts) > 1 else "",
            "full_name": name,
            "country": pdata.get("countryAcr"),
        })

    if new_players:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO players (id, first_name, last_name, full_name, country) "
                    "VALUES (:id, :first_name, :last_name, :full_name, :country) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                new_players,
            )
            conn.execute(text(
                "SELECT setval('players_id_seq', "
                "GREATEST((SELECT MAX(id) FROM players), nextval('players_id_seq') - 1) + 1)"
            ))

    # Insert tournament stubs
    if all_tournament_ids:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO tournaments (id, name) VALUES (:id, :name) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                [{"id": tid, "name": f"Tournament {tid}"} for tid in all_tournament_ids],
            )
            conn.execute(text(
                "SELECT setval('tournaments_id_seq', "
                "GREATEST((SELECT MAX(id) FROM tournaments), nextval('tournaments_id_seq') - 1) + 1)"
            ))

    # Build match rows + per-match stats
    match_rows = []
    per_match_stat_rows: list[dict] = []

    for mid, m in all_matches.items():
        match_date = _parse_match_date(m.get("date"))
        surface = _extract_match_surface(m)
        round_name = ROUND_MAP.get(m.get("roundId"))

        match_rows.append({
            "id": mid,
            "date": match_date,
            "tournament_id": m.get("tournamentId"),
            "round": round_name,
            "surface": surface,
            "player1_id": m["player1Id"],
            "player2_id": m["player2Id"],
            "winner_id": m.get("match_winner"),
            "score": m.get("result"),
        })

        for stat_map, pid_key in (
            (_PER_MATCH_STAT_KEYS_PLAYER1, "player1Id"),
            (_PER_MATCH_STAT_KEYS_PLAYER2, "player2Id"),
        ):
            stats = _extract_per_match_stats(m, stat_map)
            if stats:
                row = {
                    "player_id": m[pid_key],
                    "match_id": mid,
                    "period": "match",
                    "surface": surface,
                }
                for col in _PER_MATCH_STAT_KEYS_PLAYER1:
                    row[col] = stats.get(col)
                per_match_stat_rows.append(row)

    insert_match_sql = text("""
        INSERT INTO matches (id, date, tournament_id, round, surface,
                             player1_id, player2_id, winner_id, score)
        VALUES (:id, :date, :tournament_id, :round, :surface,
                :player1_id, :player2_id, :winner_id, :score)
        ON CONFLICT (id) DO UPDATE SET
            surface      = COALESCE(EXCLUDED.surface,      matches.surface),
            tournament_id= COALESCE(EXCLUDED.tournament_id,matches.tournament_id),
            round        = COALESCE(EXCLUDED.round,        matches.round),
            winner_id    = COALESCE(EXCLUDED.winner_id,    matches.winner_id),
            date         = COALESCE(EXCLUDED.date,         matches.date),
            score        = COALESCE(EXCLUDED.score,        matches.score)
    """)

    upserted = 0
    for i in range(0, len(match_rows), BATCH_SIZE):
        with engine.begin() as conn:
            result = conn.execute(insert_match_sql, match_rows[i: i + BATCH_SIZE])
            upserted += result.rowcount

    with engine.begin() as conn:
        conn.execute(text(
            "SELECT setval('matches_id_seq', "
            "GREATEST((SELECT MAX(id) FROM matches), nextval('matches_id_seq') - 1) + 1)"
        ))

    # Write per-match player_stats
    if per_match_stat_rows:
        match_ids_to_clear = list({r["match_id"] for r in per_match_stat_rows})
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM player_stats WHERE period = 'match' AND match_id = ANY(:mids)"),
                {"mids": match_ids_to_clear},
            )
            existing_player_ids = {
                r[0] for r in conn.execute(text("SELECT id FROM players")).fetchall()
            }
        clean_rows = [r for r in per_match_stat_rows if r["player_id"] in existing_player_ids]
        if clean_rows:
            insert_stats_sql = text("""
                INSERT INTO player_stats (
                    player_id, match_id, period, surface,
                    aces, double_faults, first_serve_pct, first_serve_win_pct,
                    second_serve_win_pct, return_points_won_pct,
                    break_points_saved_pct, break_points_converted_pct,
                    service_games_won_pct, return_games_won_pct, tiebreaks_won_pct
                ) VALUES (
                    :player_id, :match_id, :period, :surface,
                    :aces, :double_faults, :first_serve_pct, :first_serve_win_pct,
                    :second_serve_win_pct, :return_points_won_pct,
                    :break_points_saved_pct, :break_points_converted_pct,
                    :service_games_won_pct, :return_games_won_pct, :tiebreaks_won_pct
                )
            """)
            with engine.begin() as conn:
                for i in range(0, len(clean_rows), BATCH_SIZE):
                    conn.execute(insert_stats_sql, clean_rows[i: i + BATCH_SIZE])

    logger.info(
        "Matches step complete: %d upserted, %d new players, %d tournament stubs",
        upserted, len(new_players), len(all_tournament_ids),
    )
    return {
        "matches_upserted": upserted,
        "new_players": len(new_players),
        "tournament_stubs": len(all_tournament_ids),
    }


def recompute_head_to_head(engine, dry_run: bool = False) -> int:
    """
    Recompute head_to_head win counts from all matches in the DB.
    Only considers pairs where both players have a current ranking.
    Returns the number of H2H pairs upserted.
    """
    if dry_run:
        with engine.begin() as conn:
            count = conn.execute(text(
                "SELECT COUNT(DISTINCT (LEAST(m.player1_id, m.player2_id), "
                "GREATEST(m.player1_id, m.player2_id))) "
                "FROM matches m "
                "JOIN players p1 ON p1.id = m.player1_id AND p1.current_ranking IS NOT NULL "
                "JOIN players p2 ON p2.id = m.player2_id AND p2.current_ranking IS NOT NULL "
                "WHERE m.winner_id IS NOT NULL"
            )).scalar()
        logger.info("[DRY RUN] Would upsert %d H2H pairs", count or 0)
        return 0

    with engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO head_to_head (player1_id, player2_id, player1_wins, player2_wins, last_updated)
            SELECT
                LEAST(m.player1_id, m.player2_id)    AS player1_id,
                GREATEST(m.player1_id, m.player2_id) AS player2_id,
                SUM(CASE WHEN m.winner_id = LEAST(m.player1_id, m.player2_id)    THEN 1 ELSE 0 END),
                SUM(CASE WHEN m.winner_id = GREATEST(m.player1_id, m.player2_id) THEN 1 ELSE 0 END),
                NOW()
            FROM matches m
            JOIN players p1 ON p1.id = m.player1_id AND p1.current_ranking IS NOT NULL
            JOIN players p2 ON p2.id = m.player2_id AND p2.current_ranking IS NOT NULL
            WHERE m.winner_id IS NOT NULL
            GROUP BY LEAST(m.player1_id, m.player2_id), GREATEST(m.player1_id, m.player2_id)
            ON CONFLICT ON CONSTRAINT uq_h2h_players
            DO UPDATE SET
                player1_wins = EXCLUDED.player1_wins,
                player2_wins = EXCLUDED.player2_wins,
                last_updated = EXCLUDED.last_updated
        """))
        return result.rowcount


# ---------------------------------------------------------------------------
# Step wrappers
# ---------------------------------------------------------------------------

def step_1_rankings(dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would call sync_top200_rankings(top_n=200)")
        return
    sync_top200_rankings(top_n=200)


def step_2_recent_matches(engine, lookback_days: int, dry_run: bool = False) -> dict:
    return fetch_recent_matches(engine, lookback_days=lookback_days, dry_run=dry_run)


def step_3_tournament_stubs(dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would call backfill_tournaments(only_ranked_meetings=True)")
        return
    backfill_tournaments(only_ranked_meetings=True)


def step_4_player_stats(session, api_key: str, batch_size: int, dry_run: bool = False) -> dict:
    with session.bind.begin() as conn:
        ranked_ids = [
            row[0] for row in conn.execute(
                text("SELECT id FROM players WHERE current_ranking IS NOT NULL ORDER BY current_ranking")
            ).fetchall()
        ]
    logger.info("Running stats ingestion for %d ranked players", len(ranked_ids))
    return ingest_player_stats(
        session, api_key, batch_size=batch_size, player_ids=ranked_ids, dry_run=dry_run
    )


def step_5_h2h(engine, dry_run: bool = False) -> int:
    count = recompute_head_to_head(engine, dry_run=dry_run)
    logger.info("H2H pairs upserted: %d", count)
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Daily tennis database update — polls ATP API and upserts into PostgreSQL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--lookback-days", type=int, default=30, metavar="N",
                   help="Fetch matches from last N days")
    p.add_argument("--batch-size", type=int, default=50, metavar="N",
                   help="Batch size for career stats ingestion")
    p.add_argument("--skip-rankings",    action="store_true", help="Skip step 1: rankings refresh")
    p.add_argument("--skip-matches",     action="store_true", help="Skip step 2: recent match ingestion")
    p.add_argument("--skip-tournaments", action="store_true", help="Skip step 3: tournament stub fill")
    p.add_argument("--skip-stats",       action="store_true", help="Skip step 4: career stats refresh")
    p.add_argument("--skip-h2h",         action="store_true", help="Skip step 5: H2H recomputation")
    p.add_argument("--dry-run",  action="store_true", help="Fetch but do not write to the database")
    p.add_argument("--verbose",  action="store_true", help="Enable DEBUG-level logging")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    settings = get_settings()
    if not settings.tennis_api_key:
        logger.error("TENNIS_API_KEY is not set. Check your .env file.")
        return 1
    if not settings.postgres_url:
        logger.error("POSTGRES_URL is not set. Check your .env file.")
        return 1

    # Use the engine already constructed by seed_data at import time
    engine = sd_engine

    sep = "=" * 70
    logger.info(sep)
    logger.info("Tennis Scout Daily Update — %s", date.today().isoformat())
    logger.info(
        "  Lookback: %d days | Batch: %d | Dry run: %s",
        args.lookback_days, args.batch_size, args.dry_run,
    )
    logger.info(sep)

    results: dict = {}

    if not args.skip_rankings:
        logger.info("STEP 1/5: Rankings refresh")
        step_1_rankings(dry_run=args.dry_run)
        results["rankings"] = "done"

    if not args.skip_matches:
        logger.info("STEP 2/5: Recent matches (%d-day lookback)", args.lookback_days)
        results["matches"] = step_2_recent_matches(engine, args.lookback_days, dry_run=args.dry_run)

    if not args.skip_tournaments:
        logger.info("STEP 3/5: Tournament stub fill")
        step_3_tournament_stubs(dry_run=args.dry_run)
        results["tournaments"] = "done"

    if not args.skip_stats:
        logger.info("STEP 4/5: Player career stats (~17 min for 200 players)")
        session = SessionLocal()
        try:
            results["stats"] = step_4_player_stats(
                session, settings.tennis_api_key, args.batch_size, dry_run=args.dry_run
            )
        finally:
            session.close()

    if not args.skip_h2h:
        logger.info("STEP 5/5: H2H recomputation")
        results["h2h_pairs"] = step_5_h2h(engine, dry_run=args.dry_run)

    logger.info(sep)
    logger.info("Daily update complete.")
    for key, val in results.items():
        logger.info("  %-20s %s", key + ":", val)
    logger.info(sep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
