from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class HistoryCreate(BaseModel):
    feature: str
    question: str
    response: dict[str, Any] | None = None
    summary: str | None = None
    status: Literal["ok", "error"] = "ok"
    metadata: dict[str, Any] | None = None


class HistoryRead(BaseModel):
    id: uuid.UUID
    tenant_id: str
    user_id: str
    feature: str
    question: str
    summary: str | None
    status: Literal["ok", "error"]
    response: dict[str, Any] | None
    metadata: dict[str, Any] | None
    created_at: datetime
