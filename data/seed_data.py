"""
Schema-only bootstrap: drops all tables and recreates them from the current
SQLAlchemy models.  Does NOT insert any data — that will come from the
external tennis API ingestion pipeline.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine

from backend.app.config import get_settings
from backend.app.models import Base  # noqa: F401 — registers all models

settings = get_settings()
engine = create_engine(settings.postgres_url, pool_pre_ping=True)


def reset_schema() -> None:
    """Drop every table managed by Base, then recreate them."""
    print("Dropping all tables …")
    Base.metadata.drop_all(engine)
    print("Creating tables …")
    Base.metadata.create_all(engine)
    print("Schema reset complete — 0 rows inserted (data comes from API).")


if __name__ == "__main__":
    reset_schema()
