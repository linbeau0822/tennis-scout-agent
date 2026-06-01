from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import and_, or_, select
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

def _safe_avg(values: list[float | None]) -> float | None:
    """Return the average of non-None values, or None if there are no such values."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 2)


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
    """Pull recent per-match stat rows for a player (bounded to avoid huge histories)."""
    # Limit the number of per-match rows to avoid fetching an unbounded history
    # for players with very long careers. Adjust this constant if the UI needs
    # a different window of recent matches.
    MAX_PER_MATCH_ROWS = 100
    stmt = (
        select(PlayerStats)
        .where(PlayerStats.player_id == player_id, PlayerStats.match_id.is_not(None))
        .order_by(PlayerStats.match_id.desc())
        .limit(MAX_PER_MATCH_ROWS)
    )
    return list(session.scalars(stmt))


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
                "aces_per_match": None,
                "first_serve_pct": None,
                "first_serve_win_pct": None,
            },
        }

    decided = [m for m in matches if m.winner_id is not None]
    wins = sum(1 for m in decided if m.winner_id == player_id)
    losses = len(decided) - wins
    win_pct = round((wins / len(decided)) * 100, 2) if decided else 0.0
    surfaces = Counter(m.surface for m in matches if m.surface)

    # Compute averages from per-match stats if available
    if per_match_stats:
        avg_first_serve_pct = _safe_avg([s.first_serve_pct for s in per_match_stats])
        avg_first_serve_win = _safe_avg([s.first_serve_win_pct for s in per_match_stats])
        avg_aces = _safe_avg([float(s.aces) if s.aces is not None else None for s in per_match_stats])
    else:
        avg_first_serve_pct = None
        avg_first_serve_win = None
        avg_aces = None

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
        "win_pct": win_pct,
        "surface_breakdown": dict(surfaces),
        "recent_form": recent_form,
        "averages": {
            "aces_per_match": avg_aces,
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
            "image_url": player.image_url,
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


def search_players(query: str, limit: int = 8) -> list[dict]:
    q = query.strip()
    if len(q) < 2:
        return []
    limit = max(1, min(limit, 20))
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    with get_session() as session:
        rows = session.scalars(
            select(Player)
            .where(Player.full_name.ilike(pattern, escape="\\"))
            .order_by(Player.current_ranking.asc().nulls_last(), Player.full_name.asc())
            .limit(limit)
        )
        return [
            {
                "id": p.id,
                "name": p.full_name,
                "country": p.country,
                "ranking": p.current_ranking,
            }
            for p in rows
        ]


def compare_players(player_names: list[str]) -> list[dict]:
    snapshots: list[dict] = []
    for name in player_names:
        snapshot = get_player_snapshot(name)
        if snapshot:
            snapshots.append(snapshot)
    return snapshots


# ── Head-to-Head ────────────────────────────────────────────────────────────

MAX_H2H_MEETINGS = 10


def compute_h2h(session: Session, p1_id: int, p2_id: int) -> dict:
    """
    Compute the head-to-head record between two players from the matches table.

    Returns:
        {
          "player1_id": int,
          "player2_id": int,
          "record": {"player1_wins": int, "player2_wins": int,
                     "total_meetings": int, "decided": int},
          "surface_split": {
            "<surface>": {"player1_wins": int, "player2_wins": int, "matches": int}
          },
          "meetings": [
            {"match_id": int, "date": str|None, "tournament": str|None,
             "round": str|None, "surface": str|None,
             "winner_id": int|None, "winner_name": str|None,
             "score": str|None}
          ]
        }
    """
    matches = list(
        session.scalars(
            select(Match)
            .where(
                or_(
                    and_(Match.player1_id == p1_id, Match.player2_id == p2_id),
                    and_(Match.player1_id == p2_id, Match.player2_id == p1_id),
                )
            )
            .order_by(Match.date.desc().nulls_last(), Match.id.desc())
        )
    )

    p1_wins = 0
    p2_wins = 0
    decided = 0
    surface_split: dict[str, dict[str, int]] = {}
    meetings: list[dict] = []

    for m in matches:
        if m.winner_id is not None:
            decided += 1
            if m.winner_id == p1_id:
                p1_wins += 1
            elif m.winner_id == p2_id:
                p2_wins += 1

        if m.surface:
            bucket = surface_split.setdefault(
                m.surface,
                {"player1_wins": 0, "player2_wins": 0, "matches": 0},
            )
            bucket["matches"] += 1
            if m.winner_id == p1_id:
                bucket["player1_wins"] += 1
            elif m.winner_id == p2_id:
                bucket["player2_wins"] += 1

        if len(meetings) < MAX_H2H_MEETINGS:
            winner_name: str | None = None
            if m.winner_id is not None:
                if m.player1 and m.winner_id == m.player1_id:
                    winner_name = m.player1.full_name
                elif m.player2 and m.winner_id == m.player2_id:
                    winner_name = m.player2.full_name
            meetings.append({
                "match_id": m.id,
                "date": m.date.isoformat() if m.date else None,
                "tournament": m.tournament.name if m.tournament else None,
                "round": m.round,
                "surface": m.surface,
                "winner_id": m.winner_id,
                "winner_name": winner_name,
                "score": m.score,
            })

    return {
        "player1_id": p1_id,
        "player2_id": p2_id,
        "record": {
            "player1_wins": p1_wins,
            "player2_wins": p2_wins,
            "total_meetings": len(matches),
            "decided": decided,
        },
        "surface_split": surface_split,
        "meetings": meetings,
    }


def compare_players_with_h2h(player_names: list[str]) -> dict:
    """
    Build snapshots for the requested players and, when exactly two valid
    players are resolved, also compute their head-to-head record.

    Returns:
        {"snapshots": [...], "h2h": dict | None}
    """
    with get_session() as session:
        snapshots: list[dict] = []
        for name in player_names:
            snap = _get_player_snapshot_with_session(session, name)
            if snap:
                snapshots.append(snap)

        h2h: dict | None = None
        if len(snapshots) == 2:
            h2h = compute_h2h(
                session,
                snapshots[0]["player"]["id"],
                snapshots[1]["player"]["id"],
            )

        return {"snapshots": snapshots, "h2h": h2h}
