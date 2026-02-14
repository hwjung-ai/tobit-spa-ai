"""
Admin Inspector - Real-time Log Streaming
Provides WebSocket-based real-time log streaming for observability.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from core.auth import get_current_user
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspector", tags=["admin-inspector"])


class LogEntry(BaseModel):
    """Log entry structure."""
    timestamp: str
    level: str
    logger: str
    message: str
    extra: Dict[str, Any] = {}
    tenant_id: Optional[str] = None


class LogFilter(BaseModel):
    """Log filter configuration."""
    levels: List[str] = []  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    loggers: List[str] = []  # Logger name patterns
    keywords: List[str] = []  # Keywords to match
    tenant_id: Optional[str] = None


class ConnectionManager:
    """Manages WebSocket connections for log streaming."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.filters: Dict[WebSocket, LogFilter] = {}
        self._log_buffer: List[LogEntry] = []
        self._buffer_size = 1000

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.filters[websocket] = LogFilter()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        self.filters.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_log(self, log_entry: LogEntry, websocket: WebSocket):
        """Send a log entry to a specific WebSocket."""
        try:
            await websocket.send_json(log_entry.model_dump())
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

    async def broadcast_log(self, log_entry: LogEntry):
        """Broadcast a log entry to all connected WebSockets with matching filters."""
        self._add_to_buffer(log_entry)

        disconnected = set()
        for websocket in self.active_connections:
            if self._matches_filter(log_entry, self.filters.get(websocket, LogFilter())):
                try:
                    await websocket.send_json(log_entry.model_dump())
                except Exception:
                    disconnected.add(websocket)

        for ws in disconnected:
            self.disconnect(ws)

    def update_filter(self, websocket: WebSocket, log_filter: LogFilter):
        """Update the filter for a WebSocket connection."""
        self.filters[websocket] = log_filter

    def get_buffered_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent buffered logs."""
        return [log.model_dump() for log in self._log_buffer[-limit:]]

    def _add_to_buffer(self, log_entry: LogEntry):
        """Add log entry to circular buffer."""
        self._log_buffer.append(log_entry)
        if len(self._log_buffer) > self._buffer_size:
            self._log_buffer = self._log_buffer[-self._buffer_size:]

    def _matches_filter(self, log_entry: LogEntry, log_filter: LogFilter) -> bool:
        """Check if log entry matches the filter criteria."""
        # Tenant isolation - filter by tenant_id
        if log_filter.tenant_id and log_entry.tenant_id:
            if log_entry.tenant_id != log_filter.tenant_id:
                return False

        # Level filter
        if log_filter.levels and log_entry.level not in log_filter.levels:
            return False

        # Logger filter
        if log_filter.loggers:
            if not any(logger in log_entry.logger for logger in log_filter.loggers):
                return False

        # Keyword filter
        if log_filter.keywords:
            message_lower = log_entry.message.lower()
            if not any(kw.lower() in message_lower for kw in log_filter.keywords):
                return False

        return True


# Global connection manager
manager = ConnectionManager()


@router.websocket("/logs/stream")
async def websocket_log_stream(
    websocket: WebSocket,
    levels: str = Query("", description="Comma-separated log levels"),
    loggers: str = Query("", description="Comma-separated logger patterns"),
):
    """
    WebSocket endpoint for real-time log streaming.

    Query parameters:
    - levels: Comma-separated log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - loggers: Comma-separated logger name patterns

    Messages sent:
    - {"timestamp": "...", "level": "...", "logger": "...", "message": "...", "extra": {...}}
    """
    await manager.connect(websocket)

    # Apply initial filters from query params
    log_filter = LogFilter(
        levels=levels.split(",") if levels else [],
        loggers=loggers.split(",") if loggers else [],
    )
    manager.update_filter(websocket, log_filter)

    # Send recent buffered logs
    for log_data in manager.get_buffered_logs(limit=50):
        try:
            await websocket.send_json(log_data)
        except Exception:
            break

    try:
        while True:
            # Wait for filter updates from client
            data = await websocket.receive_text()
            try:
                filter_update = json.loads(data)
                if "filter" in filter_update:
                    new_filter = LogFilter(**filter_update["filter"])
                    manager.update_filter(websocket, new_filter)
                    await websocket.send_json({"type": "filter_updated", "success": True})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, description="Filter by log level"),
    logger_pattern: Optional[str] = Query(None, description="Filter by logger pattern"),
    search: Optional[str] = Query(None, description="Search in message"),
    current_user=Depends(get_current_user),
):
    """Get recent buffered logs with optional filtering. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    logs = manager.get_buffered_logs(limit=limit)

    # Apply tenant filter
    if tenant_id:
        logs = [log for log in logs if log.get("tenant_id") is None or log.get("tenant_id") == tenant_id]

    # Apply filters
    if level:
        logs = [log for log in logs if log.get("level") == level]

    if logger_pattern:
        logs = [log for log in logs if logger_pattern in log.get("logger", "")]

    if search:
        search_lower = search.lower()
        logs = [log for log in logs if search_lower in log.get("message", "").lower()]

    return {"logs": logs, "count": len(logs)}


@router.post("/logs/emit")
async def emit_test_log(
    level: str = "INFO",
    message: str = "Test log message",
    logger_name: str = "test",
    current_user=Depends(get_current_user),
):
    """Emit a test log entry (for testing the streaming). Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    log_entry = LogEntry(
        timestamp=datetime.utcnow().isoformat(),
        level=level.upper(),
        logger=logger_name,
        message=message,
        extra={"source": "test"},
        tenant_id=tenant_id,
    )
    await manager.broadcast_log(log_entry)
    return {"success": True, "log": log_entry.model_dump()}


# Custom log handler for integration with Python logging
class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that broadcasts to WebSocket clients."""

    def emit(self, record: logging.LogRecord):
        """Emit a log record to WebSocket clients."""
        try:
            log_entry = LogEntry(
                timestamp=datetime.utcfromtimestamp(record.created).isoformat(),
                level=record.levelname,
                logger=record.name,
                message=self.format(record),
                extra={
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                },
            )
            # Schedule broadcast in event loop
            asyncio.create_task(manager.broadcast_log(log_entry))
        except Exception:
            self.handleError(record)


def setup_log_streaming(level: int = logging.INFO):
    """
    Set up log streaming by adding WebSocket handler to root logger.

    Call this during application startup to enable real-time log streaming.
    """
    handler = WebSocketLogHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter('%(message)s'))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    logger.info("WebSocket log streaming enabled")
