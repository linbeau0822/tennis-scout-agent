from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.data_service import compare_players, get_player_snapshot
from app.services.llm_service import (
    build_compare_prompt,
    build_player_prompt,
    generate_report,
)

router = APIRouter(tags=["players"])


class CompareRequest(BaseModel):
    player_names: list[str] = Field(default_factory=list, min_length=2)


@router.get("/player/{name}")
def get_player_report(name: str) -> dict:
    snapshot = get_player_snapshot(name)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Player not found: {name}")

    prompt = build_player_prompt(snapshot)
    report = generate_report(prompt)

    return {**snapshot, "report": report}


@router.post("/compare")
def get_compare_report(payload: CompareRequest) -> dict:
    snapshots = compare_players(payload.player_names)

    if len(snapshots) < 2:
        raise HTTPException(
            status_code=404,
            detail="Need at least two valid player names for comparison.",
        )

    prompt = build_compare_prompt(snapshots)
    report = generate_report(prompt)

    return {
        "players": [s["player"] for s in snapshots],
        "snapshots": snapshots,
        "report": report,
    }
