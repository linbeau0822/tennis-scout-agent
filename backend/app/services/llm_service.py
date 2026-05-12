from __future__ import annotations

import hashlib
from typing import Literal, TypedDict

from openai import OpenAI

from app.config import get_settings
from app.services.cache_service import cache_get_json, cache_set_json, cache_status

settings = get_settings()


class LLMMetadata(TypedDict, total=False):
    status: Literal["available", "unavailable"]
    source: Literal["openai", "fallback"]
    model: str
    error: str
    cache: Literal["hit", "miss", "disabled"]


class ReportResult(TypedDict):
    report: str
    llm: LLMMetadata


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        print("Warning: OPENAI_API_KEY is not set. LLM features will be unavailable.")
        return None
    print("LLM client initialized with OpenAI.")
    return OpenAI(api_key=settings.openai_api_key)


def build_player_prompt(snapshot: dict) -> str:
    player = snapshot["player"]
    stats = snapshot["stats"]
    agg = snapshot.get("aggregated_stats", {})

    ranking_str = f", ranking #{player['ranking']}" if player.get("ranking") else ""
    handedness_str = f", {player['handedness']}" if player.get("handedness") else ""
    backhand_str = f" ({player['backhand_type']} backhand)" if player.get("backhand_type") else ""

    lines = [
        "You are an elite tennis analyst. Write a concise scouting report.\n",
        f"Player: {player['name']} ({player.get('country', 'N/A')}){ranking_str}{handedness_str}{backhand_str}",
        f"Matches: {stats['matches_played']} | Win%: {stats['win_pct']}",
        f"Surface breakdown: {stats['surface_breakdown']}",
        f"Recent form: {stats['recent_form']}",
        f"Serve profile: aces/match={stats['averages'].get('aces_per_match') or 'N/A'}, "
        f"1st serve pct={stats['averages'].get('first_serve_pct') or 'N/A'}, "
        f"1st serve win%={stats['averages'].get('first_serve_win_pct') or 'N/A'}",
    ]

    if agg:
        lines.append(
            f"Career stats: break_pts_saved%={agg.get('break_points_saved_pct', 'N/A')}, "
            f"break_pts_converted%={agg.get('break_points_converted_pct', 'N/A')}, "
            f"return_pts_won%={agg.get('return_points_won_pct', 'N/A')}, "
            f"service_games_won%={agg.get('service_games_won_pct', 'N/A')}"
        )

    lines.append("\nOutput sections: Strengths, Weaknesses, Matchup Advice.")
    return "\n".join(lines)


def build_compare_prompt(snapshots: list[dict], h2h: dict | None = None) -> str:
    sections = []
    for s in snapshots:
        stats = s["stats"]
        player = s["player"]
        recent = stats.get("recent_form", [])
        recent_str = ", ".join(
            f"{r['result']} vs {r['opponent']} ({r['surface']})" for r in recent[:5]
        ) or "N/A"
        ranking_str = f"#{player['ranking']}, " if player.get("ranking") else ""
        sections.append(
            f"- {player['name']} ({ranking_str}{player.get('country', 'N/A')}): "
            f"win%={stats['win_pct']}, matches={stats['matches_played']}, "
            f"surface={stats['surface_breakdown']}, "
            f"aces/match={stats['averages'].get('aces_per_match') or 'N/A'}, "
            f"1st_serve_pct={stats['averages'].get('first_serve_pct') or 'N/A'}, "
            f"1st_serve_win%={stats['averages'].get('first_serve_win_pct') or 'N/A'}, "
            f"recent form: {recent_str}"
        )

    players = "\n".join(sections)
    h2h_block = _format_h2h_for_prompt(snapshots, h2h)

    return (
        "You are an elite tennis analyst. Compare the following two players and provide a detailed"
        " head-to-head analysis with a match prediction.\n\n"
        f"Players:\n{players}\n\n"
        f"{h2h_block}\n"
        "IMPORTANT: Your prediction should NOT blindly favor the historically better player. "
        "Prioritize recent form, current physical condition/age, and surface context. "
        "When you cite the head-to-head, use ONLY the numbers above — do not invent meetings.\n\n"
        "Output the following sections using markdown headings:\n"
        "## Head-to-Head Summary\n"
        "## Recent Form\n"
        "## Strengths vs Weaknesses Matchup\n"
        "## Surface Advantage\n"
        "## Prediction\n"
        "In the Prediction section, clearly state the predicted winner and explain why with a "
        "confidence assessment."
    )


def _format_h2h_for_prompt(snapshots: list[dict], h2h: dict | None) -> str:
    """Render the head-to-head record as a compact prompt block."""
    if not h2h or len(snapshots) < 2:
        return "Head-to-head record: not available.\n"

    p1_name = snapshots[0]["player"]["name"]
    p2_name = snapshots[1]["player"]["name"]
    rec = h2h.get("record", {})
    total = rec.get("total_meetings", 0)
    p1_wins = rec.get("player1_wins", 0)
    p2_wins = rec.get("player2_wins", 0)

    if total == 0:
        return f"Head-to-head record: no prior meetings between {p1_name} and {p2_name}.\n"

    # Surface split
    surface_lines = []
    for surface, split in (h2h.get("surface_split") or {}).items():
        surface_lines.append(
            f"  - {surface}: {p1_name} {split['player1_wins']}-{split['player2_wins']} {p2_name}"
            f" ({split['matches']} match{'es' if split['matches'] != 1 else ''})"
        )

    # Last 5 meetings
    meeting_lines = []
    for m in (h2h.get("meetings") or [])[:5]:
        winner = m.get("winner_name") or ("Unknown" if m.get("winner_id") is None else "")
        date_str = m.get("date") or "date unknown"
        surface = m.get("surface") or "surface unknown"
        score = m.get("score") or ""
        tourn = m.get("tournament") or ""
        meeting_lines.append(
            f"  - {date_str} | {tourn} | {surface} | winner: {winner} | score: {score}"
        )

    parts = [
        f"Head-to-head record: {p1_name} {p1_wins}-{p2_wins} {p2_name} "
        f"({total} total meeting{'s' if total != 1 else ''}).",
    ]
    if surface_lines:
        parts.append("Surface split:")
        parts.extend(surface_lines)
    if meeting_lines:
        parts.append("Most recent meetings (newest first):")
        parts.extend(meeting_lines)
    return "\n".join(parts) + "\n"


def _cache_key(prompt: str) -> str:
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return f"llm_report:{settings.openai_model}:{digest}"


def generate_report(prompt: str) -> ReportResult:
    cache_enabled = cache_status() == "enabled"
    key = _cache_key(prompt) if cache_enabled else None

    if cache_enabled:
        cached = cache_get_json(key)
        if cached is not None:
            cached.setdefault("llm", {})["cache"] = "hit"
            return cached  # type: ignore[return-value]

    client = _client()
    if client is None:
        print("LLM client is unavailable. Returning fallback report.")
        return {
            "report": "LLM unavailable",
            "llm": {
                "status": "unavailable",
                "source": "fallback",
                "model": settings.openai_model,
                "error": "OPENAI_API_KEY is not configured",
                "cache": "miss" if cache_enabled else "disabled",
            },
        }

    try:
        print("Sending prompt to LLM...")  # Log the beginning of the prompt
        response = client.responses.create(
            model=settings.openai_model,
            input=prompt,
            temperature=0.3,
        )
        report = response.output_text.strip()

        if not report:
            print("LLM returned empty output. Returning fallback report.")
            return {
                "report": "LLM unavailable",
                "llm": {
                    "status": "unavailable",
                    "source": "fallback",
                    "model": settings.openai_model,
                    "error": "Language model returned empty output",
                    "cache": "miss" if cache_enabled else "disabled",
                },
            }

        print("LLM response received with status ", response.status)  # Log the beginning of the response
        result: ReportResult = {
            "report": report,
            "llm": {
                "status": "available",
                "source": "openai",
                "model": settings.openai_model,
                "cache": "miss" if cache_enabled else "disabled",
            },
        }
        if cache_enabled and key is not None:
            cache_set_json(key, result, settings.llm_cache_ttl_seconds)
        return result
    except Exception as e:
        print("Error during LLM request:", e)
        return {
            "report": "LLM unavailable",
            "llm": {
                "status": "unavailable",
                "source": "fallback",
                "model": settings.openai_model,
                "error": "Language model request failed",
                "cache": "miss" if cache_enabled else "disabled",
            },
        }
