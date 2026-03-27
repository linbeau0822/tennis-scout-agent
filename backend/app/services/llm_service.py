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
    players = "\n".join(
        [
            (
                f"- {s['player']['name']} (#{s['player']['ranking']}): "
                f"win%={s['stats']['win_pct']}, surface={s['stats']['surface_breakdown']}"
            )
            for s in snapshots
        ]
    )

    return (
        "You are an elite tennis analyst. Compare the following players and provide tactical"
        " recommendations.\n\n"
        f"Players:\n{players}\n\n"
        "Output sections: Best Overall Form, Surface Specialist, Tactical Notes."
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
