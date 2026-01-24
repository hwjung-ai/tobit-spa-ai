from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from schemas import ResponseEnvelope

router = APIRouter(prefix="/cep-builder", tags=["cep-builder"])

_rules: list[dict[str, str]] = [
    {
        "id": str(uuid.uuid4()),
        "name": "Busy Hours",
        "rule": '{"condition":"traffic > 80"}',
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Payment Alert",
        "rule": '{"condition":"amount > 1000"}',
    },
]


@router.get("/rules", response_model=ResponseEnvelope)
def list_rules() -> ResponseEnvelope:
    return ResponseEnvelope.success(data={"rules": _rules})


@router.post("/rules", response_model=ResponseEnvelope)
def create_rule(payload: dict[str, str]) -> ResponseEnvelope:
    new_rule = {
        "id": str(uuid.uuid4()),
        "name": payload.get("name", f"Rule {datetime.utcnow().isoformat()}"),
        "rule": payload.get("rule", "{}"),
    }
    _rules.append(new_rule)
    return ResponseEnvelope.success(data={"rule": new_rule})


@router.put("/rules/{rule_id}", response_model=ResponseEnvelope)
def update_rule(rule_id: str, payload: dict[str, str]) -> ResponseEnvelope:
    for rule in _rules:
        if rule["id"] == rule_id:
            rule["name"] = payload.get("name", rule["name"])
            rule["rule"] = payload.get("rule", rule["rule"])
            return ResponseEnvelope.success(data={"rule": rule})
    raise HTTPException(status_code=404, detail="Rule not found")


@router.delete("/rules/{rule_id}", response_model=ResponseEnvelope)
def delete_rule(rule_id: str) -> ResponseEnvelope:
    global _rules
    _rules = [rule for rule in _rules if rule["id"] != rule_id]
    return ResponseEnvelope.success(data={"deleted": rule_id})
