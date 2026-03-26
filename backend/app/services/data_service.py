from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Match, Player

settings = get_settings()
engine = create_engine(settings.postgres_url, pool_pre_ping=True)


@contextmanager
def get_session() -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def _summarize_matches(matches: list[Match]) -> dict:
    if not matches:
        return {
            "matches_played": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": 0.0,
            "surface_breakdown": {},
            "recent_form": [],
            "averages": {"ace_pct": 0.0, "first_serve_win_pct": 0.0},
        }

    wins = sum(1 for m in matches if m.result.upper() == "W")
    losses = len(matches) - wins
    surfaces = Counter(m.surface for m in matches)

    avg_ace = round(sum(m.ace_pct for m in matches) / len(matches), 2)
    avg_first_serve = round(sum(m.first_serve_win_pct for m in matches) / len(matches), 2)

    recent = sorted(matches, key=lambda m: m.played_at, reverse=True)[:5]
    recent_form = [
        {
            "date": m.played_at.isoformat(),
            "opponent": m.opponent,
            "surface": m.surface,
            "score": m.score,
            "result": m.result,
        }
        for m in recent
    ]

    return {
        "matches_played": len(matches),
        "wins": wins,
        "losses": losses,
        "win_pct": round((wins / len(matches)) * 100, 2),
        "surface_breakdown": dict(surfaces),
        "recent_form": recent_form,
        "averages": {
            "ace_pct": avg_ace,
            "first_serve_win_pct": avg_first_serve,
        },
    }


def get_player_snapshot(player_name: str) -> dict | None:
    with get_session() as session:
        player = session.scalar(
            select(Player).where(func.lower(Player.name) == player_name.strip().lower()).limit(1)
        )

        if not player:
            return None

        matches = list(
            session.scalars(
                select(Match)
                .where(Match.player_id == player.id)
                .order_by(Match.played_at.desc())
            )
        )

    return {
        "player": {
            "id": player.id,
            "name": player.name,
            "ranking": player.ranking,
            "country": player.country,
        },
        "stats": _summarize_matches(matches),
    }


def compare_players(player_names: list[str]) -> list[dict]:
    snapshots: list[dict] = []
    for name in player_names:
        snapshot = get_player_snapshot(name)
        if snapshot:
            snapshots.append(snapshot)
    return snapshots
