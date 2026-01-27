from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Literal

from pydantic import BaseModel, field_serializer


class HistoryCreate(BaseModel):
    feature: str
    question: str
    response: dict[str, Any] | None = None
    summary: str | None = None
    status: Literal["ok", "error", "processing"] = "ok"
    metadata: dict[str, Any] | None = None


class HistoryRead(BaseModel):
    id: uuid.UUID
    tenant_id: str
    user_id: str
    feature: str
    question: str
    summary: str | None
    status: Literal["ok", "error", "processing"]
    response: dict[str, Any] | None
    metadata: dict[str, Any] | None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        # Convert to KST (UTC+9)
        kst_timezone = timezone(timedelta(hours=9))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        kst_dt = dt.astimezone(kst_timezone)
        return kst_dt.isoformat()
