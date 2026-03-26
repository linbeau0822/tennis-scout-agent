from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.models import Base, Match, Player

settings = get_settings()
engine = create_engine(settings.postgres_url, pool_pre_ping=True)


def seed() -> None:
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.execute(delete(Match))
        session.execute(delete(Player))

        players = [
            Player(name="Carlos Alcaraz", ranking=3, country="ESP"),
            Player(name="Jannik Sinner", ranking=1, country="ITA"),
            Player(name="Novak Djokovic", ranking=5, country="SRB"),
        ]
        session.add_all(players)
        session.flush()

        today = date.today()
        mock_matches = [
            Match(
                player_id=players[0].id,
                opponent="Daniil Medvedev",
                surface="Hard",
                score="6-4 3-6 6-3",
                ace_pct=7.2,
                first_serve_win_pct=73.5,
                result="W",
                played_at=today - timedelta(days=2),
                raw_stats={"break_points_saved": "5/7"},
            ),
            Match(
                player_id=players[0].id,
                opponent="Alexander Zverev",
                surface="Clay",
                score="4-6 6-2 6-4",
                ace_pct=5.4,
                first_serve_win_pct=70.1,
                result="W",
                played_at=today - timedelta(days=8),
                raw_stats={"break_points_saved": "4/8"},
            ),
            Match(
                player_id=players[1].id,
                opponent="Andrey Rublev",
                surface="Hard",
                score="7-5 6-2",
                ace_pct=9.1,
                first_serve_win_pct=78.4,
                result="W",
                played_at=today - timedelta(days=1),
                raw_stats={"break_points_saved": "3/4"},
            ),
            Match(
                player_id=players[2].id,
                opponent="Stefanos Tsitsipas",
                surface="Clay",
                score="6-3 4-6 6-4",
                ace_pct=6.3,
                first_serve_win_pct=74.0,
                result="W",
                played_at=today - timedelta(days=4),
                raw_stats={"break_points_saved": "6/9"},
            ),
        ]

        session.add_all(mock_matches)
        session.commit()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
