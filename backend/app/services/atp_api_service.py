"""
Service for interacting with the ATP Tennis API.

Provides functionality to fetch player profiles and extract profile information
from the external ATP API.
"""

import time
from typing import Optional
from datetime import datetime

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


def extract_player_data_from_profile(profile: Optional[dict]) -> dict:
    """
    Extract player information from ATP API profile response.

    Args:
        profile: Player profile dictionary from API response

    Returns:
        Dictionary with keys: coach, height_cm, weight_kg, handedness,
                              backhand_type, pro_since
    """
    result = {
        "coach": None,
        "height_cm": None,
        "weight_kg": None,
        "handedness": None,
        "backhand_type": None,
        "pro_since": None,
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

    return result
