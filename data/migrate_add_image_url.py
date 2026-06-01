"""One-shot migration: add the players.image_url column.

Run once after pulling the player-photos branch:

    .venv/bin/python data/migrate_add_image_url.py

Safe to re-run thanks to `IF NOT EXISTS`.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.db import engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE players ADD COLUMN IF NOT EXISTS image_url TEXT"))
        print("OK: players.image_url is present.")


if __name__ == "__main__":
    main()
