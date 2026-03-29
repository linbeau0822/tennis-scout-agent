from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Player ──────────────────────────────────────────────────────────────────

class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    birthdate: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    handedness: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # Right / Left
    backhand_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # One-Handed / Two-Handed
    pro_since: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    matches_as_p1: Mapped[list["Match"]] = relationship(
        back_populates="player1", foreign_keys="Match.player1_id"
    )
    matches_as_p2: Mapped[list["Match"]] = relationship(
        back_populates="player2", foreign_keys="Match.player2_id"
    )
    matches_won: Mapped[list["Match"]] = relationship(
        back_populates="winner", foreign_keys="Match.winner_id"
    )
    stats: Mapped[list["PlayerStats"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    derived_stats: Mapped[list["DerivedStats"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )


# ── Tournament ──────────────────────────────────────────────────────────────

class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Grand Slam, Masters 1000, etc.
    surface: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    matches: Mapped[list["Match"]] = relationship(back_populates="tournament")


# ── Match ───────────────────────────────────────────────────────────────────

class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tournament_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tournaments.id", ondelete="SET NULL"), nullable=True
    )
    round: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # Final, SF, QF, R16, etc.
    surface: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    player1_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    player2_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    winner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    tournament: Mapped[Optional["Tournament"]] = relationship(back_populates="matches")
    player1: Mapped["Player"] = relationship(back_populates="matches_as_p1", foreign_keys=[player1_id])
    player2: Mapped["Player"] = relationship(back_populates="matches_as_p2", foreign_keys=[player2_id])
    winner: Mapped[Optional["Player"]] = relationship(back_populates="matches_won", foreign_keys=[winner_id])
    player_stats: Mapped[list["PlayerStats"]] = relationship(back_populates="match")

    __table_args__ = (
        Index("ix_matches_player1_id", "player1_id"),
        Index("ix_matches_player2_id", "player2_id"),
        Index("ix_matches_winner_id", "winner_id"),
        Index("ix_matches_tournament_id", "tournament_id"),
    )


# ── Player Stats ────────────────────────────────────────────────────────────

class PlayerStats(Base):
    __tablename__ = "player_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=True
    )
    surface: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # 'career', 'ytd', 'last_52', per-match, etc.

    # Core stat columns
    aces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    double_faults: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_serve_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_serve_win_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    second_serve_win_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_points_won_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    break_points_saved_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    break_points_converted_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    service_games_won_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_games_won_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiebreaks_won_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # JSONB fallback for additional / vendor-specific stats
    extra_stats: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="stats")
    match: Mapped[Optional["Match"]] = relationship(back_populates="player_stats")

    __table_args__ = (
        Index("ix_player_stats_player_id", "player_id"),
        Index("ix_player_stats_match_id", "match_id"),
        Index("ix_player_stats_surface", "surface"),
        Index("ix_player_stats_period", "period"),
    )


# ── Head-to-Head (optional / precomputed) ──────────────────────────────────

class HeadToHead(Base):
    __tablename__ = "head_to_head"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player1_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    player2_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    player1_wins: Mapped[int] = mapped_column(Integer, default=0)
    player2_wins: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("player1_id", "player2_id", name="uq_h2h_players"),
        Index("ix_h2h_player1_id", "player1_id"),
        Index("ix_h2h_player2_id", "player2_id"),
    )


# ── Derived Stats (cached / LLM-ready) ─────────────────────────────────────

class DerivedStats(Base):
    __tablename__ = "derived_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    stat_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. 'llm_cache', 'surface_summary'
    stats_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )

    player: Mapped["Player"] = relationship(back_populates="derived_stats")

    __table_args__ = (
        Index("ix_derived_stats_player_id", "player_id"),
        Index("ix_derived_stats_stat_type", "stat_type"),
    )
