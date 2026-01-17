from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Text, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbAssetRegistry(SQLModel, table=True):
    __tablename__ = "tb_asset_registry"

    asset_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    asset_type: str = Field(sa_column=Column(Text, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    version: int = Field(default=1, sa_column=Column(Integer, nullable=False, server_default=text("1")))
    status: str = Field(
        default="draft",
        sa_column=Column(Text, nullable=False, server_default=text("'draft'")),
    )

    # Prompt fields
    scope: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    engine: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    template: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    input_schema: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    output_contract: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Mapping fields
    mapping_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    content: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Policy fields
    policy_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    limits: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Query fields
    query_sql: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    query_params: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    query_metadata: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Screen fields
    screen_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    screen_schema: dict[str, Any] | None = Field(
        default=None, sa_column=Column("schema_json", JSONB, nullable=True)
    )

    # Common fields
    tags: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Metadata
    created_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    published_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    published_at: datetime | None = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )


class TbAssetVersionHistory(SQLModel, table=True):
    __tablename__ = "tb_asset_version_history"

    history_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    asset_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))
    version: int = Field(sa_column=Column(Integer, nullable=False))
    snapshot: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    published_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    published_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    rollback_from_version: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
