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
    player_names: list[str] = Field(default_factory=list, min_length=2, validate_default=True, description="List of player names to compare (at least 2).")


@router.get("/player/{name}")
def get_player_report(name: str) -> dict:
    snapshot = get_player_snapshot(name)
    print(f"Snapshot for {name}: {snapshot}")
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Player not found: {name}")

    prompt = build_player_prompt(snapshot)
    report_result = generate_report(prompt)

    print(f"Report result for {name}: {report_result}")
    return {**snapshot, **report_result}


@router.post("/compare")
def get_compare_report(payload: CompareRequest) -> dict:
    snapshots = compare_players(payload.player_names)

    if len(snapshots) < 2:
        found_players = {s["player"]["name"] for s in snapshots}
        invalid_players = [name for name in payload.player_names if name not in found_players]
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Need at least two valid player names for comparison.",
                "invalid_players": invalid_players,
            },
        )

    prompt = build_compare_prompt(snapshots)
    report_result = generate_report(prompt)

    return {
        "players": [s["player"] for s in snapshots],
        "snapshots": snapshots,
        **report_result,
    }
