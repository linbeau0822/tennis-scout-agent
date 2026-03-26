from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    ranking: Mapped[int] = mapped_column(Integer)
    country: Mapped[str] = mapped_column(String(3))

    matches: Mapped[list["Match"]] = relationship(back_populates="player", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    opponent: Mapped[str] = mapped_column(String(120))
    surface: Mapped[str] = mapped_column(String(20), index=True)
    score: Mapped[str] = mapped_column(String(50))
    ace_pct: Mapped[float] = mapped_column(Float)
    first_serve_win_pct: Mapped[float] = mapped_column(Float)
    result: Mapped[str] = mapped_column(String(1))
    played_at: Mapped[date] = mapped_column(Date)
    raw_stats: Mapped[dict] = mapped_column(JSONB, default=dict)

    player: Mapped["Player"] = relationship(back_populates="matches")
