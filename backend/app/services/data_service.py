from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Match, Player, PlayerStats


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _safe_avg(values: list[float | None]) -> float:
    """Return the average of non-None values, or 0.0 if empty."""
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else 0.0


def _get_matches_for_player(session: Session, player_id: int) -> list[Match]:
    """Return all matches involving a player, newest first."""
    return list(
        session.scalars(
            select(Match)
            .where(or_(Match.player1_id == player_id, Match.player2_id == player_id))
            .order_by(Match.date.desc())
        )
    )


def _opponent_name(match: Match, player_id: int) -> str:
    """Given a match, return the opponent's full_name."""
    if match.player1_id == player_id:
        return match.player2.full_name if match.player2 else "Unknown"
    return match.player1.full_name if match.player1 else "Unknown"


def _result_for(match: Match, player_id: int) -> str:
    """Return 'W' / 'L' for the given player in this match."""
    if match.winner_id is None:
        return "N/A"
    return "W" if match.winner_id == player_id else "L"


# ── Stats from PlayerStats table ───────────────────────────────────────────

def _get_aggregated_stats(session: Session, player_id: int) -> dict:
    """Pull the 'career' aggregated row from player_stats (if it exists)."""
    row: PlayerStats | None = session.scalar(
        select(PlayerStats)
        .where(PlayerStats.player_id == player_id, PlayerStats.period == "career")
        .limit(1)
    )
    if row is None:
        return {}
    return {
        "aces": row.aces,
        "double_faults": row.double_faults,
        "first_serve_pct": row.first_serve_pct,
        "first_serve_win_pct": row.first_serve_win_pct,
        "second_serve_win_pct": row.second_serve_win_pct,
        "return_points_won_pct": row.return_points_won_pct,
        "break_points_saved_pct": row.break_points_saved_pct,
        "break_points_converted_pct": row.break_points_converted_pct,
        "service_games_won_pct": row.service_games_won_pct,
        "return_games_won_pct": row.return_games_won_pct,
        "tiebreaks_won_pct": row.tiebreaks_won_pct,
        "extra_stats": row.extra_stats or {},
    }


def _get_per_match_stats(session: Session, player_id: int) -> list[PlayerStats]:
    """Pull per-match stat rows for a player."""
    return list(
        session.scalars(
            select(PlayerStats)
            .where(PlayerStats.player_id == player_id, PlayerStats.match_id.is_not(None))
            .order_by(PlayerStats.match_id.desc())
        )
    )


# ── Summarise from matches ──────────────────────────────────────────────────

def _summarize_matches(matches: list[Match], player_id: int, per_match_stats: list[PlayerStats]) -> dict:
    if not matches:
        return {
            "matches_played": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": 0.0,
            "surface_breakdown": {},
            "recent_form": [],
            "averages": {
                "ace_pct": 0.0,
                "first_serve_pct": 0.0,
                "first_serve_win_pct": 0.0,
            },
        }

    wins = sum(1 for m in matches if m.winner_id == player_id)
    losses = len(matches) - wins
    surfaces = Counter(m.surface for m in matches if m.surface)

    # Compute averages from per-match stats if available
    if per_match_stats:
        avg_first_serve_pct = _safe_avg([s.first_serve_pct for s in per_match_stats])
        avg_first_serve_win = _safe_avg([s.first_serve_win_pct for s in per_match_stats])
        avg_aces = _safe_avg([float(s.aces) if s.aces else None for s in per_match_stats])
    else:
        avg_first_serve_pct = 0.0
        avg_first_serve_win = 0.0
        avg_aces = 0.0

    recent = matches[:5]
    recent_form = [
        {
            "date": m.date.isoformat() if m.date else None,
            "opponent": _opponent_name(m, player_id),
            "surface": m.surface,
            "score": m.score,
            "result": _result_for(m, player_id),
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
            "ace_pct": avg_aces,
            "first_serve_pct": avg_first_serve_pct,
            "first_serve_win_pct": avg_first_serve_win,
        },
    }


# ── Build snapshot ──────────────────────────────────────────────────────────

def _build_snapshot(player: Player, matches: list[Match], session: Session) -> dict:
    per_match_stats = _get_per_match_stats(session, player.id)
    aggregated = _get_aggregated_stats(session, player.id)

    snapshot = {
        "player": {
            "id": player.id,
            "name": player.full_name,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "ranking": player.current_ranking,
            "country": player.country,
            "handedness": player.handedness,
            "backhand_type": player.backhand_type,
            "height_cm": player.height_cm,
            "weight_kg": player.weight_kg,
            "pro_since": player.pro_since,
            "birthdate": player.birthdate.isoformat() if player.birthdate else None,
        },
        "stats": _summarize_matches(matches, player.id, per_match_stats),
    }

    if aggregated:
        snapshot["aggregated_stats"] = aggregated

    return snapshot


# ── Public API ──────────────────────────────────────────────────────────────

def _get_player_snapshot_with_session(session: Session, player_name: str) -> dict | None:
    from sqlalchemy import func as sa_func

    player = session.scalar(
        select(Player)
        .where(sa_func.lower(Player.full_name) == player_name.strip().lower())
        .limit(1)
    )

    if not player:
        return None

    matches = _get_matches_for_player(session, player.id)
    return _build_snapshot(player, matches, session)


def get_player_snapshot(player_name: str) -> dict | None:
    with get_session() as session:
        return _get_player_snapshot_with_session(session, player_name)


def compare_players(player_names: list[str]) -> list[dict]:
    snapshots: list[dict] = []
    for name in player_names:
        snapshot = get_player_snapshot(name)
        if snapshot:
            snapshots.append(snapshot)
    return snapshots
