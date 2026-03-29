# Implement LLM Connectivity for Generate Report (Hybrid Output + Explicit Unavailable Fallback)

## Summary

Now that the MVP is complete, wire real LLM connectivity into report generation so clicking **Generate Report** returns live scouting analysis when configured.

Use a **hybrid response approach (Option B)**:
- keep existing plain-text `report` for backward compatibility
- add `llm` metadata for source/status/model

If LLM cannot be used (missing key or provider failure), return the exact fallback text:

`LLM unavailable`

## Problem

Current report generation is not exposing explicit LLM availability state. We need consistent backend and frontend behavior so users can tell whether report content is live model output or fallback.

## Goal

Implement end-to-end LLM connectivity and response metadata in the Generate Report flow:

Frontend button click → API call → `llm_service.py` model call → structured API response → UI rendering.

## Scope

### Backend

1. Update `backend/app/services/llm_service.py`
	 - Keep OpenAI request path for live generation.
	 - Return hybrid payload with:
		 - `report: string`
		 - `llm: { status, source, model, error? }`
	 - On missing key or request failure, set:
		 - `report = "LLM unavailable"`
		 - `llm.status = "unavailable"`
		 - `llm.source = "fallback"`

2. Update `backend/app/routes/player_routes.py`
	 - Ensure `/player/{name}` and `/compare` both return the hybrid report contract.
	 - Preserve existing snapshot/player fields.

3. Keep settings-driven model config from `backend/app/config.py`
	 - `OPENAI_API_KEY`
	 - `OPENAI_MODEL`

### Frontend

1. Update report rendering to consume `llm` metadata.
2. Continue displaying `report` text.
3. Show clear unavailable state when `report === "LLM unavailable"` or `llm.status === "unavailable"`.

## Proposed API Contract (Option B Hybrid)

```json
{
	"player": { "id": 1, "name": "...", "ranking": 1, "country": "..." },
	"stats": { "matches_played": 10, "wins": 8, "losses": 2 },
	"report": "Concise scouting analysis...",
	"llm": {
		"status": "available",
		"source": "openai",
		"model": "gpt-4o-mini"
	}
}
```

Fallback example:

```json
{
	"report": "LLM unavailable",
	"llm": {
		"status": "unavailable",
		"source": "fallback",
		"model": "gpt-4o-mini",
		"error": "OPENAI_API_KEY is not configured"
	}
}
```

## Acceptance Criteria

- [ ] Clicking **Generate Report** returns live LLM scouting output when `OPENAI_API_KEY` is valid.
- [ ] Response includes both `report` and `llm` metadata (hybrid contract).
- [ ] Missing API key returns exact `report` text: `LLM unavailable`.
- [ ] LLM request failures also return exact `report` text: `LLM unavailable`.
- [ ] `/player/{name}` and `/compare` endpoints use consistent report/llm behavior.
- [ ] Frontend shows clear unavailable state when fallback is returned.
- [ ] Existing stats/snapshot rendering remains unchanged.

## Out of Scope

- Multi-provider support (Anthropic, Azure OpenAI, etc.)
- Prompt optimization experiments beyond minimal production-safe tuning
- Streaming token output
- Full UI redesign

## Implementation Notes

- Keep current MVP architecture and naming conventions.
- Favor minimal, backward-compatible changes.
- Ensure errors are safe and non-sensitive in API responses.
- Update README env section if contract/config behavior changes.

## Test Plan

1. **Happy path**: valid `OPENAI_API_KEY` → report contains real model text, `llm.status=available`.
2. **No key**: unset key → `report` exactly `LLM unavailable`, `llm.status=unavailable`.
3. **Provider failure**: force API failure → same unavailable fallback behavior.
4. **Compare route**: verify identical semantics for `/compare`.
5. **Frontend**: verify fallback badge/message and no rendering regressions.
