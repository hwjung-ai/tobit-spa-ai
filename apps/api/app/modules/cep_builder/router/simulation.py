"""Simulation and validation endpoints for CEP Builder."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.common import ResponseEnvelope
from sqlmodel import Session

from ..schemas import (
    ConditionSpec,
    ConditionTemplate,
    FieldInfo,
    PreviewResult,
    ValidationResult,
)

router = APIRouter(prefix="/cep", tags=["cep-simulation"])


@router.post("/validate/condition")
def validate_condition(
    condition: ConditionSpec, payload: dict[str, Any]
) -> ResponseEnvelope:
    """Validate a single condition against test payload."""
    try:
        from ..executor import _evaluate_single_condition

        matched, refs = _evaluate_single_condition(condition.model_dump(), payload)
        result = ValidationResult(
            valid=True,
            suggestions=(
                ["Condition matched" if matched else "Condition did not match"]
            ),
        )
    except Exception as e:
        result = ValidationResult(valid=False, errors=[str(e)])
    return ResponseEnvelope.success(data={"validation": result.model_dump()})


@router.get("/condition-templates")
def get_condition_templates() -> ResponseEnvelope:
    """Get available condition templates."""
    templates = [
        ConditionTemplate(
            id="gt",
            name="Greater Than",
            description="Value exceeds threshold",
            operator=">",
            example_value=80,
            category="numeric",
        ),
        ConditionTemplate(
            id="lt",
            name="Less Than",
            description="Value is below threshold",
            operator="<",
            example_value=20,
            category="numeric",
        ),
        ConditionTemplate(
            id="eq",
            name="Equals",
            description="Value matches exactly",
            operator="==",
            example_value="error",
            category="string",
        ),
        ConditionTemplate(
            id="ne",
            name="Not Equals",
            description="Value does not match",
            operator="!=",
            example_value="success",
            category="string",
        ),
        ConditionTemplate(
            id="gte",
            name="Greater Than or Equal",
            description="Value is at or above threshold",
            operator=">=",
            example_value=70,
            category="numeric",
        ),
        ConditionTemplate(
            id="lte",
            name="Less Than or Equal",
            description="Value is at or below threshold",
            operator="<=",
            example_value=90,
            category="numeric",
        ),
    ]
    return ResponseEnvelope.success(
        data={"templates": [t.model_dump() for t in templates]}
    )


@router.post("/rules/preview")
def preview_rule(
    trigger_spec: dict[str, Any],
    conditions: list[dict[str, Any]] | None = None,
    test_payload: dict[str, Any] | None = None,
) -> ResponseEnvelope:
    """Preview rule evaluation (condition only, no action execution)."""
    try:
        from ..executor import _evaluate_composite_conditions, _evaluate_event_trigger

        if conditions:
            # Composite condition evaluation
            logic = "AND"  # default
            matched, refs = _evaluate_composite_conditions(conditions, logic, test_payload or {})
            result = PreviewResult(
                condition_matched=matched,
                would_execute=matched,
                references=refs,
                condition_evaluation_tree=refs,
            )
        else:
            # Trigger spec evaluation
            matched, refs = _evaluate_event_trigger(trigger_spec, test_payload)
            result = PreviewResult(
                condition_matched=matched,
                would_execute=matched,
                references=refs,
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseEnvelope.success(data={"preview": result.model_dump()})


@router.get("/field-suggestions")
def get_field_suggestions(search: str = "") -> ResponseEnvelope:
    """Get field suggestions for autocompletion."""
    common_fields = [
        FieldInfo(
            name="cpu",
            description="CPU usage percentage",
            type="number",
            examples=[45.2, 78.5, 92.1],
        ),
        FieldInfo(
            name="memory",
            description="Memory usage percentage",
            type="number",
            examples=[32.0, 64.5, 85.3],
        ),
        FieldInfo(
            name="disk",
            description="Disk usage percentage",
            type="number",
            examples=[50.0, 75.2, 95.8],
        ),
        FieldInfo(
            name="status",
            description="Status value",
            type="string",
            examples=["success", "error", "warning"],
        ),
        FieldInfo(
            name="count",
            description="Event count",
            type="number",
            examples=[1, 5, 10],
        ),
        FieldInfo(
            name="duration_ms",
            description="Duration in milliseconds",
            type="number",
            examples=[100, 500, 2000],
        ),
    ]

    if search:
        common_fields = [f for f in common_fields if search.lower() in f.name.lower()]

    return ResponseEnvelope.success(
        data={"fields": [f.model_dump() for f in common_fields]}
    )
