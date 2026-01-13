from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlmodel import Field, SQLModel


class RoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatThreadBase(SQLModel):
    title: str
    tenant_id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
    title_finalized: bool = Field(default=False)
    summary: str | None = None
    builder: str | None = Field(default=None, description="Optional slug of the builder that created this thread")


class ChatThread(ChatThreadBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=36)
    __tablename__ = "chat_thread"


class ChatMessageBase(SQLModel):
    thread_id: str
    role: RoleEnum
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    token_in: int | None = None
    token_out: int | None = None


class ChatMessage(ChatMessageBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=36)
    __tablename__ = "chat_message"
