from __future__ import annotations

from fastapi import HTTPException

ALLOWED_ASSUMPTIONS = {
    "traffic_change_pct",
    "cpu_change_pct",
    "memory_change_pct",
    "error_budget_change_pct",
}


def validate_assumptions(assumptions: dict[str, float | int]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in assumptions.items():
        if key not in ALLOWED_ASSUMPTIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported assumption key: {key}")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Assumption '{key}' must be numeric") from exc
        if numeric < -90 or numeric > 300:
            raise HTTPException(
                status_code=400,
                detail=f"Assumption '{key}' is out of allowed range (-90..300)",
            )
        normalized[key] = numeric
    return normalized


def validate_question(question: str) -> str:
    text = question.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Question is required")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long")
    return text
