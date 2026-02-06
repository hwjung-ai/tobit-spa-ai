"""
API Execution Log Model

Tracks execution history of API Manager APIs including performance metrics,
error tracking, and audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class ApiExecutionLog(SQLModel, table=True):
    """API execution log for tracking API runs."""
    
    __tablename__ = "api_execution_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    api_id: uuid.UUID = Field(foreign_key="api_definitions.id", nullable=False, index=True)
    
    # Execution metadata
    executed_by: str | None = Field(default=None, index=True)  # User ID or system identifier
    execution_time: datetime = Field(default_factory=datetime.utcnow, index=True)
    duration_ms: int = Field(default=0, nullable=False)
    
    # Request/Response data
    request_params: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Request parameters sent to the API"
    )
    response_data: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Response data returned from the API"
    )
    response_status: str = Field(
        default="success",
        nullable=False,
        index=True,
        description="Execution status: success, error, timeout"
    )
    
    # Error tracking
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    error_stacktrace: str | None = Field(default=None, sa_column=Column(Text))
    
    # Performance metrics
    rows_affected: int | None = Field(default=None, description="Number of rows affected (for SQL)")
    
    # Additional metadata (avoid reserved attribute name in SQLAlchemy Declarative API)
    exec_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSON),
        description="Additional execution metadata"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
