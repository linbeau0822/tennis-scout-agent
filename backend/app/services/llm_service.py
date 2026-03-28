from __future__ import annotations

from typing import Literal, TypedDict

from openai import OpenAI

from app.config import get_settings

settings = get_settings()


class LLMMetadata(TypedDict, total=False):
    status: Literal["available", "unavailable"]
    source: Literal["openai", "fallback"]
    model: str
    error: str


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

    return (
        "You are an elite tennis analyst. Write a concise scouting report.\n\n"
        f"Player: {player['name']} ({player['country']}), ranking #{player['ranking']}\n"
        f"Matches: {stats['matches_played']} | Win%: {stats['win_pct']}\n"
        f"Surface breakdown: {stats['surface_breakdown']}\n"
        f"Recent form: {stats['recent_form']}\n"
        f"Serve profile: ace%={stats['averages']['ace_pct']}, "
        f"1st serve win%={stats['averages']['first_serve_win_pct']}\n\n"
        "Output sections: Strengths, Weaknesses, Matchup Advice."
    )


def build_compare_prompt(snapshots: list[dict]) -> str:
    sections = []
    for s in snapshots:
        stats = s["stats"]
        player = s["player"]
        recent = stats.get("recent_form", [])
        recent_str = ", ".join(
            f"{r['result']} vs {r['opponent']} ({r['surface']})" for r in recent[:5]
        ) or "N/A"
        sections.append(
            f"- {player['name']} (#{player['ranking']}, {player['country']}): "
            f"win%={stats['win_pct']}, matches={stats['matches_played']}, "
            f"surface={stats['surface_breakdown']}, "
            f"ace%={stats['averages']['ace_pct']}, 1st_serve_win%={stats['averages']['first_serve_win_pct']}, "
            f"recent form: {recent_str}"
        )

    players = "\n".join(sections)

    return (
        "You are an elite tennis analyst. Compare the following two players and provide a detailed"
        " head-to-head analysis with a match prediction.\n\n"
        f"Players:\n{players}\n\n"
        "IMPORTANT: Your prediction should NOT blindly favor the historically better player. "
        "Prioritize recent form, current physical condition/age, and surface context.\n\n"
        "Output the following sections using markdown headings:\n"
        "## Head-to-Head Summary\n"
        "## Recent Form\n"
        "## Strengths vs Weaknesses Matchup\n"
        "## Surface Advantage\n"
        "## Prediction\n"
        "In the Prediction section, clearly state the predicted winner and explain why with a "
        "confidence assessment."
    )


def generate_report(prompt: str) -> ReportResult:
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
                },
            }

        print("LLM response received with status ", response.status)  # Log the beginning of the response
        return {
            "report": report,
            "llm": {
                "status": "available",
                "source": "openai",
                "model": settings.openai_model,
            },
        }
    except Exception as e:
        print("Error during LLM request:", e)
        return {
            "report": "LLM unavailable",
            "llm": {
                "status": "unavailable",
                "source": "fallback",
                "model": settings.openai_model,
                "error": "Language model request failed",
            },
        }
