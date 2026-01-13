from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class ThreadCreate(BaseModel):
    title: str | None = Field(
        default=None, description="Optional human-friendly title for the thread"
    )
    builder: str | None = Field(
        default=None, description="Optional slug of the builder that created this thread"
    )


class MessageRead(BaseModel):
    id: str
    thread_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    token_in: int | None = None
    token_out: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ThreadRead(BaseModel):
    id: str
    title: str
    tenant_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    summary: str | None = None
    title_finalized: bool = False
    builder: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ThreadDetail(ThreadRead):
    messages: List[MessageRead] = Field(default_factory=list)
