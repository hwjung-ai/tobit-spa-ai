from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from schemas import ResponseEnvelope

router = APIRouter(prefix="/ui-builder", tags=["ui-builder"])

_pages: list[dict[str, str]] = [
    {"id": str(uuid.uuid4()), "name": "Landing", "schema": '{}'},
    {"id": str(uuid.uuid4()), "name": "Dashboard", "schema": '{"type":"page"}'},
]


@router.get("/pages", response_model=ResponseEnvelope)
def list_pages() -> ResponseEnvelope:
    return ResponseEnvelope.success(data={"pages": _pages})


@router.post("/pages", response_model=ResponseEnvelope)
def create_page(payload: dict[str, str]) -> ResponseEnvelope:
    new_page = {
        "id": str(uuid.uuid4()),
        "name": payload.get("name", f"Page {datetime.utcnow().isoformat()}"),
        "schema": payload.get("schema", "{}"),
    }
    _pages.append(new_page)
    return ResponseEnvelope.success(data={"page": new_page})


@router.put("/pages/{page_id}", response_model=ResponseEnvelope)
def update_page(page_id: str, payload: dict[str, str]) -> ResponseEnvelope:
    for page in _pages:
        if page["id"] == page_id:
            page["name"] = payload.get("name", page["name"])
            page["schema"] = payload.get("schema", page["schema"])
            return ResponseEnvelope.success(data={"page": page})
    raise HTTPException(status_code=404, detail="Page not found")


@router.delete("/pages/{page_id}", response_model=ResponseEnvelope)
def delete_page(page_id: str) -> ResponseEnvelope:
    global _pages
    _pages = [page for page in _pages if page["id"] != page_id]
    return ResponseEnvelope.success(data={"deleted": page_id})
