from __future__ import annotations

from openai import OpenAI

from app.config import get_settings

settings = get_settings()


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
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


def generate_report(prompt: str) -> str:
    client = _client()
    if client is None:
        return (
            "OPENAI_API_KEY is not set. This is a local fallback report. "
            "Set OPENAI_API_KEY in .env to enable real LLM scouting analysis."
        )

    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
        temperature=0.3,
    )
    return response.output_text.strip()
