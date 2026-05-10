"""
Service for interacting with the ATP Tennis API.

Provides functionality to fetch player profiles, match histories, and extract
profile information from the external ATP API.
"""

import time
from typing import Optional
from datetime import date, datetime

import requests

from app.config import get_settings


def fetch_player_profile(player_id: int, delay: float = 1.5) -> Optional[dict]:
    """
    Fetch player profile from ATP API.

    Args:
        player_id: The ATP player ID to fetch
        delay: Delay in seconds before making the request (for rate limiting)

    Returns:
        Dictionary containing player profile data, or None if request fails
    """
    # Rate limit by adding delay
    time.sleep(delay)

    settings = get_settings()

    if not settings.tennis_api_key:
        raise ValueError("TENNIS_API_KEY not configured in environment")

    url = f"https://{settings.tennis_api_host}/tennis/v2/atp/player/profile/{player_id}"

    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": settings.tennis_api_host,
        "x-rapidapi-key": settings.tennis_api_key,
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player {player_id}: {e}")
        return None


def fetch_player_matches(
    player_id: int,
    page_size: int = 500,
    page_no: int = 1,
    delay: float = 1.5,
    max_retries: int = 5,
) -> list[dict]:
    """
    Fetch past matches for a player from ATP API.

    Includes exponential backoff retry logic for 429 (Too Many Requests) errors.

    Args:
        player_id: The ATP player ID to fetch matches for
        page_size: Number of matches per page (max 500)
        page_no: Page number to fetch
        delay: Delay in seconds before making the request (for rate limiting)
        max_retries: Maximum number of retries on 429 errors

    Returns:
        List of match dictionaries, or empty list if request fails
    """
    time.sleep(delay)

    settings = get_settings()

    if not settings.tennis_api_key:
        raise ValueError("TENNIS_API_KEY not configured in environment")

    url = (
        f"https://{settings.tennis_api_host}/tennis/v2/atp/player/"
        f"past-matches/{player_id}/?pageSize={page_size}&pageNo={page_no}"
    )

    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": settings.tennis_api_host,
        "x-rapidapi-key": settings.tennis_api_key,
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < max_retries:
                backoff = delay * (2 ** (attempt + 1))  # 3s, 6s, 12s, 24s, 48s
                print(
                    f"  ⏳ Rate limited (429) for player {player_id}, "
                    f"retrying in {backoff:.0f}s (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(backoff)
                continue
            print(f"Error fetching matches for player {player_id}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching matches for player {player_id}: {e}")
            return []


def fetch_tournament_info(
    tournament_id: int,
    delay: float = 1.5,
    max_retries: int = 5,
) -> Optional[dict]:
    """
    Fetch tournament metadata (name, court/surface, country, date, tier) from
    the ATP API. Returns the parsed `data` object or None on failure.

    Endpoint: /tennis/v2/atp/tournament/info/{id}/
    Sample response shape:
        {"data": {"id": 21323, "name": "Barcelona Open ...",
                  "court": {"id": 2, "name": "Clay"},
                  "tier": "ATP 500",
                  "date": "2026-04-13T00:00:00.000Z",
                  "coutry": {"acronym": "ESP", "name": "Spain"}}}
    """
    settings = get_settings()
    if not settings.tennis_api_key:
        raise ValueError("TENNIS_API_KEY not configured in environment")

    url = f"https://{settings.tennis_api_host}/tennis/v2/atp/tournament/info/{tournament_id}/"
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": settings.tennis_api_host,
        "x-rapidapi-key": settings.tennis_api_key,
    }

    time.sleep(delay)
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
            return payload.get("data") if isinstance(payload, dict) else None
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < max_retries:
                backoff = delay * (2 ** (attempt + 1))
                print(
                    f"  ⏳ Rate limited (429) on tournament {tournament_id}, "
                    f"retrying in {backoff:.0f}s (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(backoff)
                continue
            print(f"  Tournament fetch failed for {tournament_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"  Tournament fetch error for {tournament_id}: {e}")
            return None
    return None


def fetch_atp_rankings(
    top_n: int = 200,
    delay: float = 1.5,
    max_retries: int = 5,
    debug_log_first_response: bool = False,
) -> list[dict]:
    """
    Fetch the current ATP singles rankings from the API.

    Tries a sequence of likely endpoint paths (RapidAPI tennis hosts vary in
    their ranking-endpoint shape) and returns normalized entries:
        [{"rank": int, "player_id": int, "first_name": str,
          "last_name": str, "full_name": str, "country": str | None}, ...]

    Args:
        top_n: Maximum number of entries to return (truncates after fetching).
        delay: Seconds to wait before the request (rate limiting).
        max_retries: Retries on 429.
        debug_log_first_response: If True, prints the raw JSON of the first
            successful response (used to discover field names on initial run).

    Returns:
        List of normalized ranking dicts (may be shorter than top_n if API
        returns fewer entries). Empty list if every candidate path fails.
    """
    settings = get_settings()
    if not settings.tennis_api_key:
        raise ValueError("TENNIS_API_KEY not configured in environment")

    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": settings.tennis_api_host,
        "x-rapidapi-key": settings.tennis_api_key,
    }

    # The ranking endpoint returns ~11 entries by default; pageSize/pageNo
    # extends it. Confirmed to return 201 entries at pageSize=200.
    qs = f"?pageSize={top_n}&pageNo=1"
    # Candidate paths — try in order of plausibility. The first one that
    # returns 200 with a parseable list wins.
    candidates = [
        f"https://{settings.tennis_api_host}/tennis/v2/atp/ranking/singles/{qs}",
        f"https://{settings.tennis_api_host}/tennis/v2/atp/rankings/singles/{qs}",
        f"https://{settings.tennis_api_host}/tennis/v2/atp/ranking/{qs}",
        f"https://{settings.tennis_api_host}/tennis/v2/atp/rankings/{qs}",
    ]

    raw = None
    used_url = None
    for url in candidates:
        time.sleep(delay)
        for attempt in range(max_retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 404:
                    print(f"  Rankings endpoint not found at {url} — trying next candidate")
                    break  # try next candidate
                response.raise_for_status()
                raw = response.json()
                used_url = url
                break
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and attempt < max_retries:
                    backoff = delay * (2 ** (attempt + 1))
                    print(
                        f"  ⏳ Rate limited (429) on rankings, "
                        f"retrying in {backoff:.0f}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(backoff)
                    continue
                print(f"  Rankings fetch failed at {url}: {e}")
                break
            except requests.exceptions.RequestException as e:
                print(f"  Rankings fetch error at {url}: {e}")
                break
        if raw is not None:
            break

    if raw is None:
        print("  ✗ All rankings endpoint candidates failed.")
        return []

    print(f"  ✓ Rankings fetched from {used_url}")
    if debug_log_first_response:
        # Print just the first entry for shape inspection
        if isinstance(raw, dict) and "data" in raw:
            sample = raw["data"][:1] if isinstance(raw["data"], list) else raw["data"]
        elif isinstance(raw, list):
            sample = raw[:1]
        else:
            sample = raw
        print(f"  [debug] First ranking entry: {sample!r}")

    return _normalize_rankings_response(raw, top_n)


def _normalize_rankings_response(raw, top_n: int) -> list[dict]:
    """
    Normalize the raw rankings response into a uniform list of dicts.

    Handles common shape variants:
      - {"data": [{...}, ...]}
      - [{...}, ...]
      - {"rankings": [{...}, ...]}
    """
    if isinstance(raw, dict):
        entries = raw.get("data") or raw.get("rankings") or raw.get("items") or []
    elif isinstance(raw, list):
        entries = raw
    else:
        entries = []

    if not isinstance(entries, list):
        print(f"  Rankings entries not a list (got {type(entries).__name__}); returning empty.")
        return []

    normalized: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        rank = entry.get("rank") or entry.get("ranking") or entry.get("position")
        try:
            rank = int(rank) if rank is not None else None
        except (TypeError, ValueError):
            rank = None
        if rank is None or rank > top_n:
            continue

        # Player container can be inline or nested under "player"
        player = entry.get("player") if isinstance(entry.get("player"), dict) else entry

        pid = (
            player.get("id")
            or player.get("playerId")
            or player.get("player_id")
            or entry.get("playerId")
            or entry.get("player_id")
        )
        try:
            pid = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            pid = None
        if pid is None:
            continue

        first_name = player.get("firstName") or player.get("first_name") or ""
        last_name = player.get("lastName") or player.get("last_name") or ""
        full_name = (
            player.get("fullName")
            or player.get("full_name")
            or player.get("name")
            or f"{first_name} {last_name}".strip()
        )

        # If we only got full_name, split on first space
        if (not first_name or not last_name) and full_name:
            parts = full_name.split(" ", 1)
            first_name = first_name or parts[0]
            last_name = last_name or (parts[1] if len(parts) > 1 else "")

        country = (
            player.get("countryAcr")
            or player.get("country")
            or player.get("countryCode")
            or entry.get("countryAcr")
        )

        normalized.append({
            "rank": rank,
            "player_id": pid,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name or f"{first_name} {last_name}".strip(),
            "country": country,
        })

    normalized.sort(key=lambda r: r["rank"])
    return normalized[:top_n]


def extract_player_data_from_profile(profile: Optional[dict]) -> dict:
    """
    Extract player information from ATP API profile response.

    Args:
        profile: Player profile dictionary from API response

    Returns:
        Dictionary with keys: coach, height_cm, weight_kg, handedness,
                              backhand_type, pro_since, birthdate
    """
    result = {
        "coach": None,
        "height_cm": None,
        "weight_kg": None,
        "handedness": None,
        "backhand_type": None,
        "pro_since": None,
        "birthdate": None,
    }

    if not profile or "data" not in profile:
        return result

    data = profile.get("data", {})
    info = data.get("information", {})

    # Extract coach
    coach = info.get("coach")
    if coach:
        result["coach"] = coach if isinstance(coach, str) else coach.get("name")

    # Extract height (in cm)
    height = info.get("height")
    if height:
        try:
            result["height_cm"] = int(height)
        except (ValueError, TypeError):
            pass

    # Extract weight (in kg)
    weight = info.get("weight")
    if weight:
        try:
            result["weight_kg"] = int(weight)
        except (ValueError, TypeError):
            pass

    # Extract handedness and backhand type from "plays" field
    # Format: "Right-Handed, Two-Handed Backhand" or "Left-Handed, One-Handed Backhand"
    plays = info.get("plays", "")
    if plays:
        parts = [p.strip() for p in plays.split(",")]
        if len(parts) >= 1:
            # First part is handedness
            if "Right" in parts[0]:
                result["handedness"] = "Right"
            elif "Left" in parts[0]:
                result["handedness"] = "Left"

        if len(parts) >= 2:
            # Second part is backhand type
            if "One-Handed" in parts[1]:
                result["backhand_type"] = "One-Handed"
            elif "Two-Handed" in parts[1]:
                result["backhand_type"] = "Two-Handed"

    # Extract pro_since (year turned pro)
    turned_pro = info.get("turnedPro")
    if turned_pro:
        try:
            result["pro_since"] = int(turned_pro)
        except (ValueError, TypeError):
            pass

    # Extract birthdate. API may return it under several keys; try common ones.
    raw_dob = (
        info.get("dateOfBirth")
        or info.get("dob")
        or info.get("birthdate")
        or info.get("birthDate")
    )
    if raw_dob:
        result["birthdate"] = _parse_birthdate(raw_dob)

    return result


def _parse_birthdate(raw) -> Optional[date]:
    """Parse a birthdate from common string/dict shapes returned by the API."""
    if isinstance(raw, dict):
        # Some APIs return {"year": 2003, "month": 5, "day": 5}
        try:
            return date(int(raw["year"]), int(raw["month"]), int(raw["day"]))
        except (KeyError, TypeError, ValueError):
            return None
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    # Try ISO first, then a few common alternates
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None
