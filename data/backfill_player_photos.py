"""Backfill players.image_url from Wikipedia thumbnails.

For every player without an image_url, search Wikipedia for "{full_name} tennis",
take the top hit, and store the page's main thumbnail.

Idempotent: re-running only touches rows where image_url IS NULL.

Usage:
    .venv/bin/python data/backfill_player_photos.py
    .venv/bin/python data/backfill_player_photos.py --limit 20   # spot-check
    .venv/bin/python data/backfill_player_photos.py --refresh    # also refresh non-null rows
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Player

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "tennis-scout-agent/1.0 (https://github.com/linbeau0822/tennis-scout-agent)"
THUMB_SIZE = 400
SLEEP_BETWEEN_PLAYERS = 0.5

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def _wiki_search_title(player_name: str) -> Optional[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{player_name} tennis",
        "srlimit": 1,
        "format": "json",
    }
    resp = session.get(WIKI_API, params=params, timeout=10)
    resp.raise_for_status()
    hits = resp.json().get("query", {}).get("search", [])
    if not hits:
        return None
    return hits[0]["title"]


def _wiki_thumbnail_for_title(title: str) -> Optional[str]:
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": THUMB_SIZE,
        "format": "json",
        "redirects": 1,
    }
    resp = session.get(WIKI_API, params=params, timeout=10)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        thumb = page.get("thumbnail", {}).get("source")
        if thumb:
            return thumb
    return None


def find_photo(player_name: str) -> Optional[str]:
    title = _wiki_search_title(player_name)
    if not title:
        return None
    return _wiki_thumbnail_for_title(title)


def backfill(session_db: Session, limit: Optional[int], refresh: bool) -> tuple[int, int, int]:
    stmt = select(Player)
    if not refresh:
        stmt = stmt.where(Player.image_url.is_(None))
    stmt = stmt.order_by(Player.current_ranking.asc().nulls_last(), Player.full_name.asc())
    if limit is not None:
        stmt = stmt.limit(limit)

    players = list(session_db.scalars(stmt))
    total = len(players)
    print(f"Targeting {total} player(s).")

    filled = skipped = errored = 0
    for idx, player in enumerate(players, start=1):
        try:
            url = find_photo(player.full_name)
        except Exception as exc:
            errored += 1
            print(f"[{idx}/{total}] ERROR {player.full_name}: {exc}")
            time.sleep(SLEEP_BETWEEN_PLAYERS)
            continue

        if url:
            player.image_url = url
            session_db.commit()
            filled += 1
            print(f"[{idx}/{total}] OK    {player.full_name} -> {url[:80]}...")
        else:
            skipped += 1
            print(f"[{idx}/{total}] MISS  {player.full_name}")

        time.sleep(SLEEP_BETWEEN_PLAYERS)

    return filled, skipped, errored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only process N players.")
    parser.add_argument("--refresh", action="store_true", help="Also overwrite rows that already have image_url.")
    args = parser.parse_args()

    with SessionLocal() as db:
        filled, skipped, errored = backfill(db, args.limit, args.refresh)

    print()
    print(f"Done. Filled {filled}, missed {skipped}, errored {errored}.")


if __name__ == "__main__":
    main()
