"""
Bootstrap utilities for the tennis_scout database.

  reset_schema()  – drop & recreate all tables (destructive)
  seed_players()  – insert/upsert ATP ranking players (idempotent, safe to
                    re-run; does NOT reset schema)
  fetch_and_populate_coach_data() – fetch coach info from ATP API and populate
                    the coach column for all players (safe to re-run)
"""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, text

from app.config import get_settings
from app.models import Base
from app.services.atp_api_service import fetch_player_profile, extract_player_data_from_profile

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


if __name__ == "__main__":
    seed_players()


def fetch_and_populate_coach_data() -> None:
    """
    Fetch player information from ATP API and populate database with all available data.

    Uses a 1.5-second delay between requests to respect API rate limits.
    Updates: coach, height_cm, weight_kg, handedness, backhand_type, pro_since
    Idempotent — safe to run multiple times.
    """
    # First ensure the coach column exists (in case it's a fresh setup)
    print("Ensuring coach column exists...")
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS coach VARCHAR(120);
        """))

    # Fetch all players from database
    print("Fetching all players from database...")
    with engine.begin() as conn:
        result = conn.execute(text("SELECT id, full_name FROM players ORDER BY id"))
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
                        pro_since = :pro_since
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

