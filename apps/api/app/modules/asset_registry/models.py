from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbAssetRegistry(SQLModel, table=True):
    __tablename__ = "tb_asset_registry"
    __table_args__ = ({"extend_existing": True},)

    asset_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    asset_type: str = Field(sa_column=Column(Text, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    version: int = Field(
        default=1, sa_column=Column(Integer, nullable=False, server_default=text("1"))
    )
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
    mapping_type: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
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
    query_cypher: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    query_http: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    query_params: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    query_metadata: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Schema fields (for schema and screen assets)
    schema_json: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Screen fields
    screen_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Tool fields
    tool_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tool_config: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    tool_input_schema: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    tool_output_schema: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Common fields
    tags: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # API Manager linkage (for tools imported from API Manager)
    linked_from_api_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), nullable=True),
        description="Source API Definition ID when imported from API Manager"
    )
    linked_from_api_name: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Source API name when imported from API Manager"
    )
    linked_from_api_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="Timestamp when tool was imported from API Manager"
    )
    import_mode: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Import mode: 'api_to_tool' | 'standalone'"
    )
    last_synced_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="Last sync timestamp from source API"
    )

    # Metadata
    created_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    published_by: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    published_at: datetime | None = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )

    # Alias property for backward compatibility
    @property
    def screen_schema(self) -> dict[str, Any] | None:
        """Alias for schema_json for backward compatibility."""
        return self.schema_json

    @screen_schema.setter
    def screen_schema(self, value: dict[str, Any] | None) -> None:
        """Alias for schema_json for backward compatibility."""
        self.schema_json = value


class TbAssetVersionHistory(SQLModel, table=True):
    __tablename__ = "tb_asset_version_history"
    __table_args__ = ({"extend_existing": True},)

    history_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    asset_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))
    version: int = Field(sa_column=Column(Integer, nullable=False))
    snapshot: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    published_by: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    published_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
    rollback_from_version: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
