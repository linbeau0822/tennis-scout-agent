"""
End-to-end backfill orchestrator for the tennis_scout database.

Runs four phases sequentially, each idempotent and skippable:

  1. Sync top-N ATP rankings (extends/refreshes the players table)
  2. Profile data (coach, height, weight, handedness, backhand, pro_since, birthdate)
  3. Match history (with surface; opportunistic per-match stats)
  4. Career stats (8 mapped columns + 50+ JSONB extras)

State is written to /tmp/tennis_backfill_state.json after each phase so the
script is fully resumable. Re-running picks up at the first non-completed
phase. Use --restart to ignore prior state.

Usage:
    python backend/scripts/full_backfill.py
    python backend/scripts/full_backfill.py --top-n 200
    python backend/scripts/full_backfill.py --skip-rankings --skip-profiles
    python backend/scripts/full_backfill.py --restart
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Make backend/ and project-root/ importable
HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
PROJECT_ROOT = BACKEND_ROOT.parent
for p in (str(BACKEND_ROOT), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from data.seed_data import (  # noqa: E402
    backfill_tournaments,
    fetch_and_populate_coach_data,
    seed_matches,
    sync_top200_rankings,
)
from data_ingestion.stats_ingester import ingest_player_stats  # noqa: E402

STATE_FILE = Path("/tmp/tennis_backfill_state.json")

logger = logging.getLogger("full_backfill")


PHASES = ["rankings", "profiles", "matches", "tournaments", "stats"]


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"completed": [], "started_at": None, "history": []}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception as e:
        logger.warning("Could not read state file (%s) — starting fresh.", e)
        return {"completed": [], "started_at": None, "history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _mark_phase(state: dict[str, Any], phase: str, status: str, details: dict | None = None) -> None:
    entry = {
        "phase": phase,
        "status": status,
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    if details:
        entry["details"] = details
    state.setdefault("history", []).append(entry)
    if status == "completed" and phase not in state["completed"]:
        state["completed"].append(phase)
    _save_state(state)


def _run_rankings(state: dict, top_n: int) -> None:
    logger.info("=" * 70)
    logger.info("PHASE 1/5: Sync top-%d rankings", top_n)
    logger.info("=" * 70)
    sync_top200_rankings(top_n=top_n)
    _mark_phase(state, "rankings", "completed", {"top_n": top_n})


def _run_profiles(state: dict) -> None:
    logger.info("=" * 70)
    logger.info("PHASE 2/5: Player profile backfill (ranked only)")
    logger.info("=" * 70)
    fetch_and_populate_coach_data(only_ranked=True)
    _mark_phase(state, "profiles", "completed")


def _run_matches(state: dict) -> None:
    logger.info("=" * 70)
    logger.info("PHASE 3/5: Match history backfill")
    logger.info("=" * 70)
    seed_matches()
    _mark_phase(state, "matches", "completed")


def _run_tournaments(state: dict) -> None:
    logger.info("=" * 70)
    logger.info("PHASE 4/5: Tournament metadata + surface propagation")
    logger.info("=" * 70)
    backfill_tournaments()
    _mark_phase(state, "tournaments", "completed")


def _run_stats(state: dict) -> None:
    logger.info("=" * 70)
    logger.info("PHASE 5/5: Career stats backfill (ranked players only)")
    logger.info("=" * 70)
    settings = get_settings()
    if not settings.tennis_api_key:
        raise RuntimeError("TENNIS_API_KEY not configured")

    from sqlalchemy import text as sa_text

    session = SessionLocal()
    try:
        # Restrict career-stats ingest to currently-ranked players. The ingester
        # iterates all players by default, which would include thousands of
        # historical opponents.
        ranked_ids = [
            row[0]
            for row in session.execute(
                sa_text(
                    "SELECT id FROM players "
                    "WHERE current_ranking IS NOT NULL "
                    "ORDER BY current_ranking"
                )
            )
        ]
        logger.info("Ingesting career stats for %d ranked players.", len(ranked_ids))
        result = ingest_player_stats(
            session=session,
            api_key=settings.tennis_api_key,
            batch_size=50,
            player_ids=ranked_ids,
            dry_run=False,
        )
        logger.info("Career stats result: %s", result)
        _mark_phase(state, "stats", "completed", result)
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top-n", type=int, default=200, help="Top-N rankings to sync (default 200)")
    parser.add_argument("--skip-rankings", action="store_true", help="Skip phase 1 (rankings sync)")
    parser.add_argument("--skip-profiles", action="store_true", help="Skip phase 2 (profile backfill)")
    parser.add_argument("--skip-matches", action="store_true", help="Skip phase 3 (match backfill)")
    parser.add_argument("--skip-tournaments", action="store_true", help="Skip phase 4 (tournament metadata)")
    parser.add_argument("--skip-stats", action="store_true", help="Skip phase 5 (career stats)")
    parser.add_argument("--restart", action="store_true", help="Ignore existing state and re-run all phases")
    parser.add_argument("--verbose", action="store_true", help="DEBUG-level logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.restart and STATE_FILE.exists():
        logger.info("--restart: removing %s", STATE_FILE)
        STATE_FILE.unlink()

    state = _load_state()
    if state.get("started_at") is None:
        state["started_at"] = datetime.utcnow().isoformat() + "Z"
        _save_state(state)

    logger.info("Backfill starting. Already-completed phases: %s", state["completed"] or "(none)")
    logger.info("State file: %s", STATE_FILE)

    started = time.time()

    skips = {
        "rankings": args.skip_rankings,
        "profiles": args.skip_profiles,
        "matches": args.skip_matches,
        "tournaments": args.skip_tournaments,
        "stats": args.skip_stats,
    }
    runners = {
        "rankings": lambda: _run_rankings(state, args.top_n),
        "profiles": lambda: _run_profiles(state),
        "matches": lambda: _run_matches(state),
        "tournaments": lambda: _run_tournaments(state),
        "stats": lambda: _run_stats(state),
    }

    failed_phase = None

    for phase in PHASES:
        if phase in state["completed"]:
            logger.info("⤳ Skipping phase '%s' (already completed in this state file).", phase)
            continue
        if skips[phase]:
            logger.info("⤳ Skipping phase '%s' (--skip-%s).", phase, phase)
            continue

        logger.info("\n▶ Running phase: %s", phase)
        try:
            runners[phase]()
        except Exception as e:
            logger.exception("✗ Phase '%s' failed: %s", phase, e)
            _mark_phase(state, phase, "failed", {"error": str(e)})
            failed_phase = phase
            break

    elapsed = time.time() - started
    logger.info("=" * 70)
    logger.info("Backfill orchestrator finished in %d min %d sec", int(elapsed // 60), int(elapsed % 60))
    logger.info("Completed phases: %s", state["completed"])
    if failed_phase:
        logger.error("Stopped at failed phase: %s — re-run to resume.", failed_phase)
        return 1
    logger.info("All requested phases done. ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
