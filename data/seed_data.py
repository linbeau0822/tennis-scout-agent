"""
Bootstrap utilities for the tennis_scout database.

  reset_schema()  – drop & recreate all tables (destructive)
  seed_players()  – insert/upsert ATP ranking players (idempotent, safe to
                    re-run; does NOT reset schema)
  fetch_and_populate_coach_data() – fetch coach info from ATP API and populate
                    the coach column for all players (safe to re-run)  seed_matches()  – fetch 500 most recent matches per player from ATP API
                    and populate matches + tournaments tables (idempotent)"""

from __future__ import annotations

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, text

from app.config import get_settings
from app.models import Base
from app.services.atp_api_service import (
    fetch_atp_rankings,
    fetch_player_matches,
    fetch_player_profile,
    fetch_tournament_info,
    extract_player_data_from_profile,
)

settings = get_settings()
engine = create_engine(settings.postgres_url, pool_pre_ping=True)

# ---------------------------------------------------------------------------
# ATP ranking snapshot — 2026-03-30
# Fields not available in source JSON are left as None and can be filled in
# later via separate ingestion / migration scripts.
# ---------------------------------------------------------------------------
ATP_PLAYERS = [
    {"id": 68074, "full_name": "Carlos Alcaraz",      "first_name": "Carlos",  "last_name": "Alcaraz",         "country": "ESP", "current_ranking": 1},
    {"id": 47275, "full_name": "Jannik Sinner",        "first_name": "Jannik",  "last_name": "Sinner",          "country": "ITA", "current_ranking": 2},
    {"id": 24008, "full_name": "Alexander Zverev",     "first_name": "Alexander","last_name": "Zverev",         "country": "GER", "current_ranking": 3},
    {"id":  5992, "full_name": "Novak Djokovic",       "first_name": "Novak",   "last_name": "Djokovic",        "country": "SRB", "current_ranking": 4},
    {"id": 63572, "full_name": "Lorenzo Musetti",      "first_name": "Lorenzo", "last_name": "Musetti",         "country": "ITA", "current_ranking": 5},
    {"id": 39309, "full_name": "Alex De Minaur",       "first_name": "Alex",    "last_name": "De Minaur",       "country": "AUS", "current_ranking": 6},
    {"id": 40434, "full_name": "Felix Auger Aliassime","first_name": "Felix",   "last_name": "Auger Aliassime", "country": "CAN", "current_ranking": 7},
    {"id": 29932, "full_name": "Taylor Fritz",         "first_name": "Taylor",  "last_name": "Fritz",           "country": "USA", "current_ranking": 8},
    {"id": 87562, "full_name": "Ben Shelton",          "first_name": "Ben",     "last_name": "Shelton",         "country": "USA", "current_ranking": 9},
    {"id": 22807, "full_name": "Daniil Medvedev",      "first_name": "Daniil",  "last_name": "Medvedev",        "country": "RUS", "current_ranking": 10},
    {"id": 24245, "full_name": "Alexander Bublik",     "first_name": "Alexander","last_name": "Bublik",         "country": "KAZ", "current_ranking": 11},
    {"id": 33648, "full_name": "Casper Ruud",          "first_name": "Casper",  "last_name": "Ruud",            "country": "NOR", "current_ranking": 12},
    {"id": 67546, "full_name": "Flavio Cobolli",       "first_name": "Flavio",  "last_name": "Cobolli",         "country": "ITA", "current_ranking": 13},
    {"id": 61838, "full_name": "Jiri Lehecka",         "first_name": "Jiri",    "last_name": "Lehecka",         "country": "CZE", "current_ranking": 14},
    {"id": 25543, "full_name": "Karen Khachanov",      "first_name": "Karen",   "last_name": "Khachanov",       "country": "RUS", "current_ranking": 15},
    {"id": 29372, "full_name": "Andrey Rublev",        "first_name": "Andrey",  "last_name": "Rublev",          "country": "RUS", "current_ranking": 16},
    {"id": 36519, "full_name": "Alejandro Davidovich Fokina","first_name": "Alejandro","last_name": "Davidovich Fokina","country": "ESP", "current_ranking": 17},
    {"id": 29939, "full_name": "Frances Tiafoe",       "first_name": "Frances", "last_name": "Tiafoe",          "country": "USA", "current_ranking": 18},
    {"id": 76127, "full_name": "Luciano Darderi",      "first_name": "Luciano", "last_name": "Darderi",         "country": "ITA", "current_ranking": 19},
    {"id": 52279, "full_name": "Francisco Cerundolo",  "first_name": "Francisco","last_name": "Cerundolo",       "country": "ARG", "current_ranking": 20},
    {"id": 29935, "full_name": "Tommy Paul",           "first_name": "Tommy",   "last_name": "Paul",            "country": "USA", "current_ranking": 21},
    {"id": 93452, "full_name": "Learner Tien",         "first_name": "Learner", "last_name": "Tien",            "country": "USA", "current_ranking": 22},
    {"id": 36594, "full_name": "Valentin Vacherot",    "first_name": "Valentin","last_name": "Vacherot",         "country": "MON", "current_ranking": 23},
    {"id": 27851, "full_name": "Cameron Norrie",       "first_name": "Cameron", "last_name": "Norrie",          "country": "GBR", "current_ranking": 24},
    {"id": 63017, "full_name": "Jack Draper",          "first_name": "Jack",    "last_name": "Draper",          "country": "GBR", "current_ranking": 25},
    {"id": 86691, "full_name": "Jakub Mensik",         "first_name": "Jakub",   "last_name": "Mensik",          "country": "CZE", "current_ranking": 26},
    {"id": 28170, "full_name": "Arthur Rinderknech",   "first_name": "Arthur",  "last_name": "Rinderknech",     "country": "FRA", "current_ranking": 27},
    {"id": 83135, "full_name": "Arthur Fils",          "first_name": "Arthur",  "last_name": "Fils",            "country": "FRA", "current_ranking": 28},
    {"id": 69471, "full_name": "Holger Rune",          "first_name": "Holger",  "last_name": "Rune",            "country": "DEN", "current_ranking": 29},
    {"id": 33860, "full_name": "Tallon Griekspoor",    "first_name": "Tallon",  "last_name": "Griekspoor",      "country": "NED", "current_ranking": 30},
    {"id": 37532, "full_name": "Tomas Martin Etcheverry","first_name": "Tomas", "last_name": "Martin Etcheverry","country": "ARG", "current_ranking": 31},
    {"id": 36263, "full_name": "Corentin Moutet",      "first_name": "Corentin","last_name": "Moutet",          "country": "FRA", "current_ranking": 32},
    {"id": 56846, "full_name": "Brandon Nakashima",    "first_name": "Brandon", "last_name": "Nakashima",       "country": "USA", "current_ranking": 33},
    {"id": 38911, "full_name": "Ugo Humbert",          "first_name": "Ugo",     "last_name": "Humbert",         "country": "FRA", "current_ranking": 34},
    {"id": 92985, "full_name": "Alex Michelsen",       "first_name": "Alex",    "last_name": "Michelsen",       "country": "USA", "current_ranking": 35},
    {"id": 68627, "full_name": "Gabriel Diallo",       "first_name": "Gabriel", "last_name": "Diallo",          "country": "CAN", "current_ranking": 36},
    {"id": 31358, "full_name": "Jaume Antoni Munar Clar","first_name": "Jaume", "last_name": "Antoni Munar Clar","country": "ESP", "current_ranking": 37},
    {"id": 33502, "full_name": "Denis Shapovalov",     "first_name": "Denis",   "last_name": "Shapovalov",      "country": "CAN", "current_ranking": 38},
    {"id": 30087, "full_name": "Alejandro Tabilo",     "first_name": "Alejandro","last_name": "Tabilo",         "country": "CHI", "current_ranking": 39},
    {"id": 91521, "full_name": "Joao Fonseca",         "first_name": "Joao",    "last_name": "Fonseca",         "country": "BRA", "current_ranking": 40},
    {"id": 40609, "full_name": "Jenson Brooksby",      "first_name": "Jenson",  "last_name": "Brooksby",        "country": "USA", "current_ranking": 41},
    {"id": 42451, "full_name": "Sebastian Korda",      "first_name": "Sebastian","last_name": "Korda",          "country": "USA", "current_ranking": 42},
    {"id":  7806, "full_name": "Adrian Mannarino",     "first_name": "Adrian",  "last_name": "Mannarino",       "country": "FRA", "current_ranking": 43},
    {"id": 67535, "full_name": "Terence Atmane",       "first_name": "Terence", "last_name": "Atmane",          "country": "FRA", "current_ranking": 44},
    {"id": 34233, "full_name": "Alexei Popyrin",       "first_name": "Alexei",  "last_name": "Popyrin",         "country": "AUS", "current_ranking": 45},
    {"id": 37741, "full_name": "Zizou Bergs",          "first_name": "Zizou",   "last_name": "Bergs",           "country": "BEL", "current_ranking": 46},
    {"id": 52140, "full_name": "Fabian Marozsan",      "first_name": "Fabian",  "last_name": "Marozsan",        "country": "HUN", "current_ranking": 47},
    {"id": 31446, "full_name": "Nuno Borges",          "first_name": "Nuno",    "last_name": "Borges",          "country": "POR", "current_ranking": 48},
    {"id": 30470, "full_name": "Stefanos Tsitsipas",   "first_name": "Stefanos","last_name": "Tsitsipas",       "country": "GRE", "current_ranking": 49},
    {"id": 52721, "full_name": "Sebastian Baez",       "first_name": "Sebastian","last_name": "Baez",          "country": "ARG", "current_ranking": 50},
    {"id": 13674, "full_name": "Marton Fucsovics",     "first_name": "Marton",  "last_name": "Fucsovics",       "country": "HUN", "current_ranking": 51},
    {"id": 29732, "full_name": "Daniel Altmaier",      "first_name": "Daniel",  "last_name": "Altmaier",        "country": "GER", "current_ranking": 52},
    {"id": 28898, "full_name": "Kamil Majchrzak",      "first_name": "Kamil",   "last_name": "Majchrzak",       "country": "POL", "current_ranking": 53},
    {"id":  6101, "full_name": "Marin Cilic",          "first_name": "Marin",   "last_name": "Cilic",           "country": "CRO", "current_ranking": 54},
    {"id": 58327, "full_name": "Tomas Machac",         "first_name": "Tomas",   "last_name": "Machac",          "country": "CZE", "current_ranking": 55},
    {"id": 82269, "full_name": "Ethan Quinn",          "first_name": "Ethan",   "last_name": "Quinn",           "country": "USA", "current_ranking": 56},
    {"id": 71174, "full_name": "Giovanni Mpetshi Perricard","first_name": "Giovanni","last_name": "Mpetshi Perricard","country": "FRA", "current_ranking": 57},
    {"id": 34337, "full_name": "Miomir Kecmanovic",    "first_name": "Miomir",  "last_name": "Kecmanovic",      "country": "SRB", "current_ranking": 58},
    {"id": 79113, "full_name": "Ignacio Buse",         "first_name": "Ignacio", "last_name": "Buse",            "country": "PER", "current_ranking": 59},
    {"id": 66828, "full_name": "Mariano Navone",       "first_name": "Mariano", "last_name": "Navone",          "country": "ARG", "current_ranking": 60},
    {"id": 14856, "full_name": "Yannick Hanfmann",     "first_name": "Yannick", "last_name": "Hanfmann",        "country": "GER", "current_ranking": 61},
    {"id": 24249, "full_name": "Botic Van De Zandschulp","first_name": "Botic", "last_name": "Van De Zandschulp","country": "NED", "current_ranking": 62},
    {"id": 31392, "full_name": "Lorenzo Sonego",       "first_name": "Lorenzo", "last_name": "Sonego",          "country": "ITA", "current_ranking": 63},
    {"id": 28087, "full_name": "Reilly Opelka",        "first_name": "Reilly",  "last_name": "Opelka",          "country": "USA", "current_ranking": 64},
    {"id": 84235, "full_name": "Raphael Collignon",    "first_name": "Raphael", "last_name": "Collignon",       "country": "BEL", "current_ranking": 65},
    {"id": 18736, "full_name": "Marcos Giron",         "first_name": "Marcos",  "last_name": "Giron",           "country": "USA", "current_ranking": 66},
    {"id": 42229, "full_name": "Camilo Ugo Carabelli", "first_name": "Camilo",  "last_name": "Ugo Carabelli",   "country": "ARG", "current_ranking": 67},
    {"id": 70873, "full_name": "Arthur Cazaux",        "first_name": "Arthur",  "last_name": "Cazaux",          "country": "FRA", "current_ranking": 68},
    {"id": 52934, "full_name": "Juan Manuel Cerundolo","first_name": "Juan",    "last_name": "Manuel Cerundolo","country": "ARG", "current_ranking": 69},
    {"id": 42971, "full_name": "Vit Kopriva",          "first_name": "Vit",     "last_name": "Kopriva",         "country": "CZE", "current_ranking": 70},
    {"id": 61857, "full_name": "Valentin Royer",       "first_name": "Valentin","last_name": "Royer",          "country": "FRA", "current_ranking": 71},
    {"id": 26473, "full_name": "Hubert Hurkacz",       "first_name": "Hubert",  "last_name": "Hurkacz",         "country": "POL", "current_ranking": 72},
    {"id": 72578, "full_name": "Mattia Bellucci",      "first_name": "Mattia",  "last_name": "Bellucci",        "country": "ITA", "current_ranking": 73},
    {"id": 13447, "full_name": "Damir Dzumhur",        "first_name": "Damir",   "last_name": "Dzumhur",         "country": "BIH", "current_ranking": 74},
    {"id": 14177, "full_name": "Jan-Lennard Struff",   "first_name": "Jan-Lennard","last_name": "Struff",        "country": "GER", "current_ranking": 75},
    {"id": 64891, "full_name": "Alexander Shevchenko", "first_name": "Alexander","last_name": "Shevchenko",     "country": "KAZ", "current_ranking": 76},
    {"id": 70705, "full_name": "Roman Andres Burruchaga","first_name": "Roman", "last_name": "Andres Burruchaga","country": "ARG", "current_ranking": 77},
    {"id": 27547, "full_name": "Sebastian Ofner",      "first_name": "Sebastian","last_name": "Ofner",          "country": "AUT", "current_ranking": 78},
    {"id": 71083, "full_name": "Eliot Spizzirri",      "first_name": "Eliot",   "last_name": "Spizzirri",       "country": "USA", "current_ranking": 79},
    {"id":  1837, "full_name": "Roberto Bautista Agut","first_name": "Roberto", "last_name": "Bautista Agut",   "country": "ESP", "current_ranking": 80},
    {"id": 79060, "full_name": "Hamad Medjedovic",     "first_name": "Hamad",   "last_name": "Medjedovic",      "country": "SRB", "current_ranking": 81},
    {"id": 73620, "full_name": "Zachary Svajda",       "first_name": "Zachary", "last_name": "Svajda",          "country": "USA", "current_ranking": 82},
    {"id": 52394, "full_name": "Thiago Agustin Tirante","first_name": "Thiago", "last_name": "Agustin Tirante", "country": "ARG", "current_ranking": 83},
    {"id": 28267, "full_name": "Aleksandar Vukic",     "first_name": "Aleksandar","last_name": "Vukic",         "country": "AUS", "current_ranking": 84},
    {"id": 39152, "full_name": "Aleksandar Kovacevic", "first_name": "Aleksandar","last_name": "Kovacevic",     "country": "USA", "current_ranking": 85},
    {"id": 51417, "full_name": "Filip Misolic",        "first_name": "Filip",   "last_name": "Misolic",         "country": "AUT", "current_ranking": 86},
    {"id": 61971, "full_name": "Francisco Comesana",   "first_name": "Francisco","last_name": "Comesana",       "country": "ARG", "current_ranking": 87},
    {"id": 14432, "full_name": "Pablo Carreno-Busta",  "first_name": "Pablo",   "last_name": "Carreno-Busta",   "country": "ESP", "current_ranking": 88},
    {"id": 99691, "full_name": "Rafael Jodar",         "first_name": "Rafael",  "last_name": "Jodar",           "country": "ESP", "current_ranking": 89},
    {"id": 25171, "full_name": "Quentin Halys",        "first_name": "Quentin", "last_name": "Halys",           "country": "FRA", "current_ranking": 90},
    {"id": 29812, "full_name": "Matteo Berrettini",    "first_name": "Matteo",  "last_name": "Berrettini",      "country": "ITA", "current_ranking": 91},
    {"id": 88766, "full_name": "Alexander Blockx",     "first_name": "Alexander","last_name": "Blockx",         "country": "BEL", "current_ranking": 92},
    {"id": 11953, "full_name": "Grigor Dimitrov",      "first_name": "Grigor",  "last_name": "Dimitrov",        "country": "BUL", "current_ranking": 93},
    {"id": 28108, "full_name": "Alexandre Muller",     "first_name": "Alexandre","last_name": "Muller",         "country": "FRA", "current_ranking": 94},
    {"id": 11517, "full_name": "James Duckworth",      "first_name": "James",   "last_name": "Duckworth",       "country": "AUS", "current_ranking": 95},
    {"id": 46718, "full_name": "Patrick Kypson",       "first_name": "Patrick", "last_name": "Kypson",          "country": "USA", "current_ranking": 96},
    {"id": 68090, "full_name": "Jacob Fearnley",       "first_name": "Jacob",   "last_name": "Fearnley",        "country": "GBR", "current_ranking": 97},
    {"id":  1092, "full_name": "Stan Wawrinka",        "first_name": "Stan",    "last_name": "Wawrinka",        "country": "SUI", "current_ranking": 98},
    {"id": 59166, "full_name": "Jesper De Jong",       "first_name": "Jesper",  "last_name": "De Jong",         "country": "NED", "current_ranking": 99},
    {"id": 24840, "full_name": "Cristian Garin",       "first_name": "Cristian","last_name": "Garin",          "country": "CHI", "current_ranking": 100},
    {"id": 80391, "full_name": "Adolfo Daniel Vallejo","first_name": "Adolfo",  "last_name": "Daniel Vallejo",  "country": "PAR", "current_ranking": 101},
]


def reset_schema() -> None:
    """Drop every table managed by Base, then recreate them."""
    print("Dropping all tables …")
    Base.metadata.drop_all(engine)
    print("Creating tables …")
    Base.metadata.create_all(engine)
    print("Schema reset complete — 0 rows inserted (data comes from API).")


def seed_players() -> None:
    """
    Insert the ATP ranking player list into the players table.

    Uses INSERT … ON CONFLICT (id) DO NOTHING so the function is fully
    idempotent — safe to run multiple times without creating duplicates.
    After the insert the sequence is advanced past the highest explicit id
    so future auto-incremented rows never collide.
    """
    insert_sql = text("""
        INSERT INTO players (
            id, first_name, last_name, full_name, country, current_ranking,
            birthdate, height_cm, weight_kg, handedness, backhand_type, pro_since
        ) VALUES (
            :id, :first_name, :last_name, :full_name, :country, :current_ranking,
            NULL, NULL, NULL, NULL, NULL, NULL
        )
        ON CONFLICT (id) DO NOTHING
    """)

    advance_seq_sql = text("""
        SELECT setval(
            'players_id_seq',
            GREATEST((SELECT MAX(id) FROM players), nextval('players_id_seq') - 1) + 1
        )
    """)

    with engine.begin() as conn:
        result = conn.execute(insert_sql, ATP_PLAYERS)
        print(f"Inserted {result.rowcount} new player(s) (skipped existing).")
        conn.execute(advance_seq_sql)
        print("Sequence players_id_seq advanced past max explicit id.")


def sync_top200_rankings(top_n: int = 200) -> None:
    """
    Fetch the live top-N ATP rankings and upsert them into the players table.

    For new player IDs: insert a full row (id, names, full_name, country, rank).
    For existing IDs: only refresh `current_ranking` (don't overwrite the
    curated names/country we already have).

    Players currently ranked outside the top-N keep their old `current_ranking`
    value (we do NOT clear ranks for missing players — that would invalidate
    the existing 101 seed). If you want a clean refresh, call reset_schema()
    first.

    Idempotent — safe to re-run.
    """
    print(f"Fetching top {top_n} ATP rankings from API...")
    rankings = fetch_atp_rankings(top_n=top_n, debug_log_first_response=True)

    if not rankings:
        print("✗ No ranking entries returned from API. Aborting.")
        return

    print(f"✓ Got {len(rankings)} ranking entries from API.")

    # Insert new players: full row, ON CONFLICT DO NOTHING
    insert_sql = text("""
        INSERT INTO players (
            id, first_name, last_name, full_name, country, current_ranking,
            birthdate, height_cm, weight_kg, handedness, backhand_type, pro_since
        ) VALUES (
            :id, :first_name, :last_name, :full_name, :country, :current_ranking,
            NULL, NULL, NULL, NULL, NULL, NULL
        )
        ON CONFLICT (id) DO NOTHING
    """)

    # Update ranking for already-existing rows (run separately so we don't
    # clobber curated names/country).
    update_rank_sql = text("""
        UPDATE players SET current_ranking = :current_ranking WHERE id = :id
    """)

    advance_seq_sql = text("""
        SELECT setval(
            'players_id_seq',
            GREATEST((SELECT MAX(id) FROM players), nextval('players_id_seq') - 1) + 1
        )
    """)

    rows = []
    for r in rankings:
        # Defensive: make sure full_name is unique-ish; the players table has
        # a UNIQUE constraint on full_name. Append id only if name collides.
        full_name = r["full_name"] or f"{r['first_name']} {r['last_name']}".strip()
        if not full_name:
            full_name = f"Player {r['player_id']}"
        rows.append({
            "id": r["player_id"],
            "first_name": r["first_name"] or "",
            "last_name": r["last_name"] or "",
            "full_name": full_name,
            "country": r["country"],
            "current_ranking": r["rank"],
        })

    # Resolve full_name collisions against existing DB rows that have a
    # different id (UNIQUE constraint will reject otherwise).
    with engine.begin() as conn:
        existing = {
            row[1].lower(): row[0]
            for row in conn.execute(text("SELECT id, full_name FROM players")).fetchall()
        }
        # Drop any new entries whose full_name collides with a different id —
        # they're almost certainly the same person under a slight name variant
        # already in the DB; we just refresh the existing row's rank.
        deduped = []
        for row in rows:
            key = row["full_name"].lower()
            existing_id = existing.get(key)
            if existing_id is not None and existing_id != row["id"]:
                # Same name, different id → assume it's the same player; just
                # update the existing id's ranking.
                conn.execute(update_rank_sql, {
                    "id": existing_id,
                    "current_ranking": row["current_ranking"],
                })
                continue
            deduped.append(row)

        # Now insert (skips on id-conflict)
        result = conn.execute(insert_sql, deduped)
        inserted = result.rowcount
        # Update rankings for all top-N entries (including just-inserted ones —
        # cheap and ensures rank is current for everyone).
        conn.execute(update_rank_sql, deduped)
        conn.execute(advance_seq_sql)

    print(f"✓ Inserted {inserted} new player(s); refreshed ranking for {len(deduped)} entries.")


# ---------------------------------------------------------------------------
# Round ID → human-readable round name mapping (from ATP API)
# ---------------------------------------------------------------------------
ROUND_MAP = {
    4: "R128",
    5: "R64",
    6: "R32",
    7: "R16",
    9: "Quarters",
    10: "Semis",
    12: "Finals",
}


def _extract_match_surface(m: dict) -> str | None:
    """Best-effort surface extraction from a past-matches response entry."""
    # Try direct keys first
    for key in ("surface", "court", "courtType", "surfaceType", "groundType"):
        v = m.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            name = v.get("name") or v.get("type")
            if isinstance(name, str) and name.strip():
                return name.strip()
    # Try nested under tournament
    t = m.get("tournament") if isinstance(m.get("tournament"), dict) else {}
    for key in ("surface", "court", "surfaceType"):
        v = t.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


# Field name candidates for per-player per-match stats. We probe each match
# dict for these and, if any are found, write a PlayerStats row. The mapping
# is intentionally permissive — the actual API may use different keys, in
# which case nothing will be written and we fall back to career stats.
_PER_MATCH_STAT_KEYS_PLAYER1 = {
    "aces": ["player1Aces", "p1Aces", "aces1", "acesPlayer1"],
    "double_faults": ["player1DoubleFaults", "p1DoubleFaults", "doubleFaults1"],
    "first_serve_pct": ["player1FirstServePercentage", "p1FirstServePercentage", "firstServePercentage1"],
    "first_serve_win_pct": ["player1FirstServeWonPercentage", "p1FirstServeWonPercentage", "winningOnFirstServePercentage1"],
    "second_serve_win_pct": ["player1SecondServeWonPercentage", "p1SecondServeWonPercentage", "winningOnSecondServePercentage1"],
    "break_points_saved_pct": ["player1BreakPointsSavedPercentage", "p1BreakPointsSavedPercentage"],
    "break_points_converted_pct": ["player1BreakPointsConvertedPercentage", "p1BreakPointsConvertedPercentage"],
    "service_games_won_pct": ["player1ServiceGamesWonPercentage", "p1ServiceGamesWonPercentage"],
    "return_games_won_pct": ["player1ReturnGamesWonPercentage", "p1ReturnGamesWonPercentage"],
    "return_points_won_pct": ["player1ReturnPointsWonPercentage", "p1ReturnPointsWonPercentage"],
    "tiebreaks_won_pct": ["player1TiebreaksWonPercentage", "p1TiebreaksWonPercentage"],
}

_PER_MATCH_STAT_KEYS_PLAYER2 = {
    col: [k.replace("player1", "player2").replace("p1", "p2").replace("1", "2") for k in keys]
    for col, keys in _PER_MATCH_STAT_KEYS_PLAYER1.items()
}


def _coerce_number(v):
    """Best-effort numeric coercion; returns None if not coercible."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        s = str(v).strip().rstrip("%")
        if "." in s:
            return float(s)
        return int(s)
    except (ValueError, TypeError):
        return None


def _extract_per_match_stats(m: dict, player_field_map: dict) -> dict | None:
    """
    Extract per-match stats for a single player from a match dict, using a
    column→candidate-keys map. Returns None if nothing found.
    """
    out: dict = {}
    for col, candidates in player_field_map.items():
        for k in candidates:
            if k in m and m[k] not in (None, ""):
                v = _coerce_number(m[k])
                if v is not None:
                    out[col] = v
                    break
    return out or None


def seed_matches() -> None:
    """
    Fetch the 500 most recent matches for every player in the players table
    via the ATP API and populate the matches (and tournaments) tables.

    Workflow:
      1. Read all player IDs from the players table.
      2. For each player, call the past-matches API endpoint.
      3. Deduplicate matches globally (two seeded players may share a match).
      4. Insert any unknown opponents into the players table (minimal rows).
      5. Insert any unknown tournament IDs into the tournaments table.
      6. Bulk-insert all unique matches (with surface).
      7. Opportunistically write per-match player_stats rows if the API
         response carries per-match stat fields.

    Fully idempotent — UPSERT on conflict for surface so re-runs backfill it.
    """
    from datetime import date as date_type

    # -- 1. Load only seeded players (those with a ranking) from the DB --------
    print("Fetching all players from database...")
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT id, full_name FROM players "
                "WHERE current_ranking IS NOT NULL "
                "ORDER BY current_ranking"
            )
        )
        players = rows.fetchall()

    total_players = len(players)
    print(f"Found {total_players} players to process.")
    print("Starting to fetch match history from ATP API (1.5s delay between requests)...\n")

    # -- 2. Fetch matches per player & deduplicate ----------------------------
    all_matches: dict[int, dict] = {}      # match API id → raw dict
    all_player_refs: dict[int, dict] = {}  # player API id → {id, name, countryAcr}
    all_tournament_ids: set[int] = set()
    error_count = 0
    debug_dumped = False  # Print first match dict once for shape inspection

    for idx, (player_id, player_name) in enumerate(players, 1):
        try:
            matches = fetch_player_matches(player_id, delay=1.5)

            if not debug_dumped and matches:
                print(f"  [debug] First match dict keys: {sorted(matches[0].keys())}")
                print(f"  [debug] First match sample: {matches[0]!r}")
                debug_dumped = True

            new = 0
            for m in matches:
                mid = int(m["id"])
                if mid not in all_matches:
                    all_matches[mid] = m
                    new += 1

                # Collect every player reference for opponent resolution
                for pkey in ("player1", "player2"):
                    p = m.get(pkey, {})
                    pid = p.get("id")
                    if pid and pid not in all_player_refs:
                        all_player_refs[pid] = p

                # Collect tournament IDs
                tid = m.get("tournamentId")
                if tid:
                    all_tournament_ids.add(tid)

            print(f"[{idx}/{total_players}] ✓ {player_name} — {len(matches)} matches fetched, {new} new unique")
        except Exception as e:
            print(f"[{idx}/{total_players}] ✗ {player_name} — ERROR: {e}")
            error_count += 1

    print(f"\nAPI fetch complete. {len(all_matches)} unique matches collected, {error_count} errors.")

    if not all_matches:
        print("No matches to insert — done.")
        return

    # -- 3. Insert unknown opponents into the players table -------------------
    # Gather IDs already in the DB
    with engine.begin() as conn:
        existing_ids = set(
            r[0] for r in conn.execute(text("SELECT id FROM players")).fetchall()
        )

    new_players = []
    seen_full_names: set[str] = set()
    # Also collect existing full_names from the DB to avoid unique constraint violations
    with engine.begin() as conn:
        existing_names = set(
            r[0].lower() for r in conn.execute(text("SELECT full_name FROM players")).fetchall()
        )

    for pid, pdata in all_player_refs.items():
        if pid not in existing_ids:
            name = pdata.get("name", "Unknown")
            # Handle "Unknown Player" or blank names — make unique by appending player ID
            if not name or name.strip().lower() in ("unknown", "unknown player", ""):
                name = f"Unknown Player {pid}"
            # Deduplicate by full_name (case-insensitive) across both DB and this batch
            if name.lower() in existing_names or name.lower() in seen_full_names:
                continue
            seen_full_names.add(name.lower())
            parts = name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
            new_players.append({
                "id": pid,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": name,
                "country": pdata.get("countryAcr"),
            })

    if new_players:
        print(f"Inserting {len(new_players)} new opponent player(s)...")
        insert_player_sql = text("""
            INSERT INTO players (id, first_name, last_name, full_name, country)
            VALUES (:id, :first_name, :last_name, :full_name, :country)
            ON CONFLICT (id) DO NOTHING
        """)
        with engine.begin() as conn:
            conn.execute(insert_player_sql, new_players)
            # Advance the players sequence past the max explicit id
            conn.execute(text("""
                SELECT setval(
                    'players_id_seq',
                    GREATEST((SELECT MAX(id) FROM players), nextval('players_id_seq') - 1) + 1
                )
            """))
        print("Opponent players inserted.")
    else:
        print("No new opponent players to insert.")

    # -- 4. Insert tournament stubs -------------------------------------------
    if all_tournament_ids:
        print(f"Inserting {len(all_tournament_ids)} tournament stub(s)...")
        insert_tournament_sql = text("""
            INSERT INTO tournaments (id, name)
            VALUES (:id, :name)
            ON CONFLICT (id) DO NOTHING
        """)
        tournament_rows = [{"id": tid, "name": f"Tournament {tid}"} for tid in all_tournament_ids]
        with engine.begin() as conn:
            conn.execute(insert_tournament_sql, tournament_rows)
            conn.execute(text("""
                SELECT setval(
                    'tournaments_id_seq',
                    GREATEST((SELECT MAX(id) FROM tournaments), nextval('tournaments_id_seq') - 1) + 1
                )
            """))
        print("Tournament stubs inserted.")

    # -- 5. Bulk-insert matches (with surface) --------------------------------
    print(f"Inserting/updating {len(all_matches)} match(es)...")

    # Collect (player_id, match_id, period='match', stats) rows opportunistically
    per_match_stat_rows: list[dict] = []
    surface_seen = 0

    match_rows = []
    for mid, m in all_matches.items():
        # Parse date
        match_date = None
        raw_date = m.get("date")
        if raw_date:
            try:
                match_date = date_type.fromisoformat(raw_date[:10])
            except (ValueError, TypeError):
                pass

        # Map roundId → round name
        round_id = m.get("roundId")
        round_name = ROUND_MAP.get(round_id)

        surface = _extract_match_surface(m)
        if surface:
            surface_seen += 1

        match_rows.append({
            "id": mid,
            "date": match_date,
            "tournament_id": m.get("tournamentId"),
            "round": round_name,
            "surface": surface,
            "player1_id": m["player1Id"],
            "player2_id": m["player2Id"],
            "winner_id": m.get("match_winner"),
            "score": m.get("result"),
        })

        # Per-match stats (opportunistic) — for player1 and player2
        p1_stats = _extract_per_match_stats(m, _PER_MATCH_STAT_KEYS_PLAYER1)
        p2_stats = _extract_per_match_stats(m, _PER_MATCH_STAT_KEYS_PLAYER2)
        if p1_stats:
            per_match_stat_rows.append({
                "player_id": m["player1Id"],
                "match_id": mid,
                "period": "match",
                "surface": surface,
                **{col: p1_stats.get(col) for col in _PER_MATCH_STAT_KEYS_PLAYER1.keys()},
            })
        if p2_stats:
            per_match_stat_rows.append({
                "player_id": m["player2Id"],
                "match_id": mid,
                "period": "match",
                "surface": surface,
                **{col: p2_stats.get(col) for col in _PER_MATCH_STAT_KEYS_PLAYER2.keys()},
            })

    print(f"  Surface populated for {surface_seen}/{len(match_rows)} matches.")

    # UPSERT — keep new fields current on re-run (especially `surface`, which
    # was previously dropped on insert).
    insert_match_sql = text("""
        INSERT INTO matches (id, date, tournament_id, round, surface,
                             player1_id, player2_id, winner_id, score)
        VALUES (:id, :date, :tournament_id, :round, :surface,
                :player1_id, :player2_id, :winner_id, :score)
        ON CONFLICT (id) DO UPDATE SET
            surface = COALESCE(EXCLUDED.surface, matches.surface),
            tournament_id = COALESCE(EXCLUDED.tournament_id, matches.tournament_id),
            round = COALESCE(EXCLUDED.round, matches.round),
            winner_id = COALESCE(EXCLUDED.winner_id, matches.winner_id),
            date = COALESCE(EXCLUDED.date, matches.date),
            score = COALESCE(EXCLUDED.score, matches.score)
    """)

    BATCH_SIZE = 500
    inserted_total = 0
    for i in range(0, len(match_rows), BATCH_SIZE):
        batch = match_rows[i : i + BATCH_SIZE]
        with engine.begin() as conn:
            result = conn.execute(insert_match_sql, batch)
            inserted_total += result.rowcount

    # Advance the matches sequence
    with engine.begin() as conn:
        conn.execute(text("""
            SELECT setval(
                'matches_id_seq',
                GREATEST((SELECT MAX(id) FROM matches), nextval('matches_id_seq') - 1) + 1
            )
        """))

    # -- 6. Per-match player_stats rows (opportunistic) -----------------------
    per_match_inserted = 0
    if per_match_stat_rows:
        print(f"Writing {len(per_match_stat_rows)} per-match player_stats row(s)...")
        match_ids_to_clear = list({r["match_id"] for r in per_match_stat_rows})
        # Clear any prior period='match' rows for these match_ids so re-runs
        # are idempotent (no unique constraint to ON CONFLICT against).
        with engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM player_stats "
                    "WHERE period = 'match' AND match_id = ANY(:mids)"
                ),
                {"mids": match_ids_to_clear},
            )

        # Filter out rows whose player_id is not in players (ON DELETE CASCADE
        # foreign key would reject otherwise). All player1/player2 ids should
        # be present after Phase 4 (opponent insertion above) but be safe.
        with engine.begin() as conn:
            existing_player_ids = {
                r[0] for r in conn.execute(text("SELECT id FROM players")).fetchall()
            }
        clean_rows = [r for r in per_match_stat_rows if r["player_id"] in existing_player_ids]

        insert_stats_sql = text("""
            INSERT INTO player_stats (
                player_id, match_id, period, surface,
                aces, double_faults, first_serve_pct, first_serve_win_pct,
                second_serve_win_pct, return_points_won_pct,
                break_points_saved_pct, break_points_converted_pct,
                service_games_won_pct, return_games_won_pct, tiebreaks_won_pct
            ) VALUES (
                :player_id, :match_id, :period, :surface,
                :aces, :double_faults, :first_serve_pct, :first_serve_win_pct,
                :second_serve_win_pct, :return_points_won_pct,
                :break_points_saved_pct, :break_points_converted_pct,
                :service_games_won_pct, :return_games_won_pct, :tiebreaks_won_pct
            )
        """)

        # Ensure every row has all keys (defaulting to None) so the bind works
        all_cols = list(_PER_MATCH_STAT_KEYS_PLAYER1.keys())
        for r in clean_rows:
            for c in all_cols:
                r.setdefault(c, None)

        with engine.begin() as conn:
            for i in range(0, len(clean_rows), BATCH_SIZE):
                batch = clean_rows[i : i + BATCH_SIZE]
                result = conn.execute(insert_stats_sql, batch)
                per_match_inserted += result.rowcount
    else:
        print("  No per-match stat fields found in API response — skipping.")
        print("  (Career stats from Phase 4 ingester will still be available.)")

    print(f"Inserted/updated {inserted_total} match row(s).")
    print("\n" + "=" * 70)
    print("Match seeding complete!")
    print(f"  Unique matches collected:    {len(all_matches)}")
    print(f"  Match rows upserted:         {inserted_total}")
    print(f"  Surface populated on rows:   {surface_seen}")
    print(f"  Per-match stat rows written: {per_match_inserted}")
    print(f"  New opponent players:        {len(new_players)}")
    print(f"  Tournament stubs:            {len(all_tournament_ids)}")
    print(f"  Player fetch errors:         {error_count}")
    print("=" * 70)


def backfill_tournaments(only_ranked_meetings: bool = True) -> None:
    """
    Fetch full tournament metadata (name, surface, country, date, tier) from
    the ATP API and propagate the resulting surface to each match referencing
    that tournament.

    By default (`only_ranked_meetings=True`), only fetches info for tournaments
    that host at least one match between two currently-ranked players — the
    set that matters for top-200 H2H analysis. Tournaments with surface
    already populated are skipped (idempotent across runs).

    Set `only_ranked_meetings=False` to backfill every tournament_id in the
    tournaments table (slow: 5000+ tournaments at 1.5s each).

    Workflow:
      1. Pick tournament IDs to fetch (filtered + missing-surface only).
      2. For each, call /tennis/v2/atp/tournament/info/{id}/.
      3. UPDATE tournaments SET name, surface, location, start_date, category.
      4. UPDATE matches SET surface = tournaments.surface WHERE
         matches.tournament_id = tournaments.id AND matches.surface IS NULL.

    Surface values come from the tournament's `court.name` (e.g. "Clay", "Hard").
    """
    from datetime import datetime

    if only_ranked_meetings:
        print("Picking tournaments hosting matches between two ranked players (missing surface)...")
        sql = """
            SELECT DISTINCT m.tournament_id
            FROM matches m
            JOIN players p1 ON p1.id = m.player1_id AND p1.current_ranking IS NOT NULL
            JOIN players p2 ON p2.id = m.player2_id AND p2.current_ranking IS NOT NULL
            JOIN tournaments t ON t.id = m.tournament_id
            WHERE m.tournament_id IS NOT NULL
              AND (t.surface IS NULL OR t.surface = '')
            ORDER BY m.tournament_id
        """
    else:
        print("Picking ALL tournaments missing surface...")
        sql = """
            SELECT id FROM tournaments
            WHERE surface IS NULL OR surface = ''
            ORDER BY id
        """

    with engine.begin() as conn:
        rows = conn.execute(text(sql)).fetchall()
    tids = [r[0] for r in rows]

    total = len(tids)
    if total == 0:
        print("No tournaments in DB — run --matches first.")
        return

    print(f"Found {total} tournaments. Fetching info from API (1.5s delay)...\n")
    updated = 0
    error_count = 0

    update_sql = text("""
        UPDATE tournaments
        SET name = COALESCE(:name, name),
            surface = COALESCE(:surface, surface),
            location = COALESCE(:location, location),
            start_date = COALESCE(:start_date, start_date),
            category = COALESCE(:category, category)
        WHERE id = :id
    """)

    for idx, tid in enumerate(tids, 1):
        try:
            info = fetch_tournament_info(tid, delay=1.5)
            if not info:
                print(f"[{idx}/{total}] ✗ Tournament {tid} — no data")
                error_count += 1
                continue

            # Surface from court.name
            surface = None
            court = info.get("court")
            if isinstance(court, dict):
                surface = court.get("name")
            if not surface and isinstance(info.get("courtId"), int):
                # If court name missing, leave null
                surface = None

            # Location from country.name (or "coutry" — yes the API has a typo)
            location = None
            country = info.get("country") or info.get("coutry")
            if isinstance(country, dict):
                location = country.get("name")

            # Start date
            start_date = None
            raw_date = info.get("date") or info.get("startDate")
            if raw_date:
                try:
                    start_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
                except (ValueError, TypeError):
                    pass

            with engine.begin() as conn:
                conn.execute(update_sql, {
                    "id": tid,
                    "name": info.get("name"),
                    "surface": surface,
                    "location": location,
                    "start_date": start_date,
                    "category": info.get("tier"),
                })

            print(f"[{idx}/{total}] ✓ Tournament {tid} — {info.get('name')!r} | surface={surface} | tier={info.get('tier')}")
            updated += 1

        except Exception as e:
            print(f"[{idx}/{total}] ✗ Tournament {tid} — ERROR: {e}")
            error_count += 1

    # Propagate surface from tournaments → matches
    print("\nPropagating surface from tournaments → matches...")
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE matches
            SET surface = tournaments.surface
            FROM tournaments
            WHERE matches.tournament_id = tournaments.id
              AND tournaments.surface IS NOT NULL
              AND (matches.surface IS NULL OR matches.surface = '')
        """))
        propagated = result.rowcount

    # Also propagate to any per-match player_stats rows we already wrote
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE player_stats AS ps
            SET surface = m.surface
            FROM matches m
            WHERE ps.match_id = m.id
              AND m.surface IS NOT NULL
              AND (ps.surface IS NULL OR ps.surface = '')
        """))

    print("=" * 70)
    print("Tournament backfill complete!")
    print(f"  Tournaments updated: {updated}")
    print(f"  Errors:              {error_count}")
    print(f"  Match rows surfaced: {propagated}")
    print("=" * 70)


def fetch_and_populate_coach_data(only_ranked: bool = True) -> None:
    """
    Fetch player information from ATP API and populate database with all available data.

    Uses a 1.5-second delay between requests to respect API rate limits.
    Updates: coach, height_cm, weight_kg, handedness, backhand_type,
             pro_since, birthdate
    Idempotent — safe to run multiple times.

    Args:
        only_ranked: If True (default), only process players with a non-null
            `current_ranking` (i.e. the seeded/synced top-N). If False, process
            every player in the table — includes thousands of historical
            opponents and is expensive.
    """
    # First ensure the coach column exists (in case it's a fresh setup)
    print("Ensuring coach column exists...")
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS coach VARCHAR(120);
        """))

    # Fetch players from database (filtered to ranked by default)
    where_clause = "WHERE current_ranking IS NOT NULL" if only_ranked else ""
    order_clause = "ORDER BY current_ranking" if only_ranked else "ORDER BY id"
    print(f"Fetching players from database ({'ranked only' if only_ranked else 'all'})...")
    with engine.begin() as conn:
        result = conn.execute(
            text(f"SELECT id, full_name FROM players {where_clause} {order_clause}")
        )
        players = result.fetchall()

    total_players = len(players)
    updated_count = 0
    error_count = 0

    print(f"Found {total_players} players to process.")
    print("Starting to fetch player data from ATP API (1.5s delay between requests)...\n")

    for idx, (player_id, player_name) in enumerate(players, 1):
        try:
            # Fetch profile from API
            profile = fetch_player_profile(player_id, delay=1.5)
            player_data = extract_player_data_from_profile(profile)

            # Update database with all extracted fields
            with engine.begin() as conn:
                update_sql = text("""
                    UPDATE players
                    SET coach = :coach,
                        height_cm = :height_cm,
                        weight_kg = :weight_kg,
                        handedness = :handedness,
                        backhand_type = :backhand_type,
                        pro_since = :pro_since,
                        birthdate = COALESCE(:birthdate, birthdate)
                    WHERE id = :id
                """)
                result = conn.execute(update_sql, {
                    "id": player_id,
                    "coach": player_data["coach"],
                    "height_cm": player_data["height_cm"],
                    "weight_kg": player_data["weight_kg"],
                    "handedness": player_data["handedness"],
                    "backhand_type": player_data["backhand_type"],
                    "pro_since": player_data["pro_since"],
                    "birthdate": player_data.get("birthdate"),
                })

            # Build status message with populated fields
            status_parts = []
            if player_data["coach"]:
                status_parts.append(f"Coach: {player_data['coach']}")
            if player_data["height_cm"]:
                status_parts.append(f"Height: {player_data['height_cm']}cm")
            if player_data["weight_kg"]:
                status_parts.append(f"Weight: {player_data['weight_kg']}kg")
            if player_data["handedness"]:
                status_parts.append(f"Handedness: {player_data['handedness']}")
            if player_data["backhand_type"]:
                status_parts.append(f"Backhand: {player_data['backhand_type']}")
            if player_data["pro_since"]:
                status_parts.append(f"Pro Since: {player_data['pro_since']}")
            if player_data.get("birthdate"):
                status_parts.append(f"DOB: {player_data['birthdate']}")

            status = f"✓ {player_name}"
            if status_parts:
                status += " | " + ", ".join(status_parts)

            print(f"[{idx}/{total_players}] {status}")
            updated_count += 1

        except Exception as e:
            print(f"[{idx}/{total_players}] ✗ {player_name} → ERROR: {e}")
            error_count += 1

    print("\n" + "=" * 70)
    print(f"Player data population complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total processed: {updated_count + error_count}/{total_players}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tennis Scout DB bootstrap utilities")
    parser.add_argument("--reset", action="store_true", help="Drop & recreate all tables")
    parser.add_argument("--players", action="store_true", help="Seed players table from hardcoded list")
    parser.add_argument("--sync-rankings", action="store_true", help="Sync top-200 rankings from API")
    parser.add_argument("--coaches", action="store_true", help="Fetch & populate coach/profile data")
    parser.add_argument("--matches", action="store_true", help="Fetch & populate matches")
    parser.add_argument("--tournaments", action="store_true", help="Fetch tournament info & propagate surface to matches")
    parser.add_argument("--top-n", type=int, default=200, help="Top-N rankings to sync (default 200)")
    args = parser.parse_args()

    # Default to --players if no flag is given
    if not any([args.reset, args.players, args.sync_rankings, args.coaches, args.matches, args.tournaments]):
        args.players = True

    if args.reset:
        reset_schema()
    if args.players:
        seed_players()
    if args.sync_rankings:
        sync_top200_rankings(top_n=args.top_n)
    if args.coaches:
        fetch_and_populate_coach_data()
    if args.matches:
        seed_matches()
    if args.tournaments:
        backfill_tournaments()
