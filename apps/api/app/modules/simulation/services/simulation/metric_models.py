"""
SQLModel for metric timeseries table.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, Column, Float, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel


class TbMetricTimeseries(SQLModel, table=True):
    """Timeseries metric data for simulation baseline and backtesting."""

    __tablename__ = "tb_metric_timeseries"
    __table_args__ = ({"extend_existing": True},)

    id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        description="Unique identifier (UUID)",
    )
    tenant_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Tenant identifier",
    )
    service: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Service name (e.g., api-gateway)",
    )
    metric_name: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Metric name (latency_ms, throughput_rps, error_rate_pct, cost_usd_hour)",
    )
    timestamp: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, index=True, server_default="now()"
        ),
        description="Measurement timestamp",
    )
    value: float = Field(
        sa_column=Column(Float, nullable=False),
        description="Metric value",
    )
    unit: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Unit (ms, rps, %, USD/h)",
    )
    tags: dict[str, str] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Additional metadata tags",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default="now()"
        ),
        description="Record creation timestamp",
    )
