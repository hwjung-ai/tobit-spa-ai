from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import TIMESTAMP, Column, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class TbExecutionTrace(SQLModel, table=True):
    __tablename__ = "tb_execution_trace"
    __table_args__ = ({"extend_existing": True},)

    trace_id: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
    )
    parent_trace_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
    )
    feature: str = Field(sa_column=Column(Text, nullable=False))
    endpoint: str = Field(sa_column=Column(Text, nullable=False))
    method: str = Field(sa_column=Column(Text, nullable=False))
    ops_mode: str = Field(sa_column=Column(Text, nullable=False))
    question: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(
        default="success",
        sa_column=Column(Text, nullable=False, server_default=text("'success'")),
    )
    duration_ms: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
    )
    request_payload: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    applied_assets: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    asset_versions: List[str] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    fallbacks: Dict[str, bool] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    plan_raw: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    plan_validated: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    execution_steps: List[Dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    references: List[Dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    answer: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    ui_render: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    audit_links: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    flow_spans: List[Dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    # New fields for orchestration
    route: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    stage_inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True),
    )
    stage_outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True),
    )
    replan_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )


class TbGoldenQuery(SQLModel, table=True):
    """Golden query baseline for regression detection"""

    __tablename__ = "tb_golden_query"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
        description="Unique identifier for golden query",
    )
    name: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Display name for the golden query",
    )
    query_text: str = Field(
        sa_column=Column(Text, nullable=False),
        description="The actual question/query text",
    )
    ops_type: str = Field(
        sa_column=Column(Text, nullable=False),
        description="OPS type: all|config|history|metric|relation|graph|hist",
    )
    options: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Query options (mode, timeout, filters, etc)",
    )
    enabled: bool = Field(
        default=True,
        sa_column=Column(Text, nullable=False, server_default=text("true")),
        description="Enable/disable regression checking for this query",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )


class TbRegressionBaseline(SQLModel, table=True):
    """Baseline trace for regression detection"""

    __tablename__ = "tb_regression_baseline"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
        description="Unique identifier",
    )
    golden_query_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Foreign key to TbGoldenQuery",
    )
    baseline_trace_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Trace ID of the baseline execution",
    )
    baseline_status: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Status of baseline trace (success|error)",
    )
    asset_versions: List[str] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Asset versions at baseline time",
    )
    created_by: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="User who set the baseline",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )


class TbRegressionRun(SQLModel, table=True):
    """Regression detection run result"""

    __tablename__ = "tb_regression_run"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
        description="Unique identifier",
    )
    golden_query_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Foreign key to TbGoldenQuery",
    )
    baseline_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Foreign key to TbRegressionBaseline",
    )
    candidate_trace_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Trace ID of the candidate execution",
    )
    baseline_trace_id: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Cached baseline trace ID for quick access",
    )
    judgment: str = Field(
        sa_column=Column(Text, nullable=False),
        description="PASS|WARN|FAIL - deterministic regression result",
    )
    verdict_reason: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Human-readable reason for judgment",
    )
    diff_summary: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Cached diff summary (change counts by section)",
    )
    triggered_by: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Trigger source: manual|asset_change|schedule",
    )
    trigger_info: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Trigger details (asset_id, schedule_name, etc)",
    )
    execution_duration_ms: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
        description="Duration of candidate execution in milliseconds",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )


class TbRegressionRuleConfig(SQLModel, table=True):
    """Configurable judgment rules for regression detection (v2)"""

    __tablename__ = "tb_regression_rule_config"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
        description="Unique identifier (UUID)",
    )
    golden_query_id: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
        description="Applied to specific golden query (or 'global' for default)",
    )

    # FAIL thresholds (triggers FAIL if matched)
    max_assets_changed: int = Field(
        default=0,
        description="Max assets allowed to change (0 = no change)",
    )
    plan_intent_change_allowed: bool = Field(
        default=False,
        description="Allow plan intent changes without FAIL",
    )
    tool_calls_failed_threshold: int = Field(
        default=0,
        description="Max tool call failures allowed (0 = no failures allowed)",
    )
    blocks_structure_variance_threshold: float = Field(
        default=0.5,
        description="Max block structure change (0.5 = 50%)",
    )

    # WARN thresholds (triggers WARN if matched)
    tool_calls_added_threshold: int = Field(
        default=1,
        description="Max tool calls added (before WARN)",
    )
    references_variance_threshold: float = Field(
        default=0.25,
        description="Max references variance (0.25 = 25%)",
    )
    tool_duration_spike_factor: float = Field(
        default=2.0,
        description="Max tool duration multiplier (2.0 = 2x)",
    )

    # Enabled rules
    check_assets_changed: bool = Field(default=True)
    check_plan_intent: bool = Field(default=True)
    check_tool_errors: bool = Field(default=True)
    check_block_structure: bool = Field(default=True)
    check_tool_duration: bool = Field(default=True)
    check_references_variance: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
    updated_by: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="User who last updated (optional)",
    )
