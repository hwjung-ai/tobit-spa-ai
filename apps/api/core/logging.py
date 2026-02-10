from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_REQUEST_CONTEXT: ContextVar[dict[str, str]] = ContextVar(
    "request_context",
    default={
        "request_id": "-",
        "tenant_id": "-",
        "mode": "-",
        "trace_id": "-",
        "parent_trace_id": "-",
    },
)

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "api.log"


def get_request_context() -> dict[str, str]:
    context = _REQUEST_CONTEXT.get()
    return {
        "request_id": context.get("request_id", "-"),
        "tenant_id": context.get("tenant_id", "-"),
        "mode": context.get("mode", "-"),
        "trace_id": context.get("trace_id", "-"),
        "parent_trace_id": context.get("parent_trace_id", "-"),
    }


def set_request_context(
    request_id: str,
    tenant_id: str,
    mode: str = "ci",
    trace_id: str = "",
    parent_trace_id: str = "",
) -> None:
    _REQUEST_CONTEXT.set(
        {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "mode": mode,
            "trace_id": trace_id or request_id,
            "parent_trace_id": parent_trace_id or "-",
        }
    )


def clear_request_context() -> None:
    _REQUEST_CONTEXT.set(
        {
            "request_id": "-",
            "tenant_id": "-",
            "mode": "-",
            "trace_id": "-",
            "parent_trace_id": "-",
        }
    )


class StructuredFormatter(logging.Formatter):
    STANDARD_ATTRS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "process",
        "processName",
        "message",
        "request_id",
        "tenant_id",
        "mode",
        "trace_id",
        "parent_trace_id",
    }

    def __init__(self) -> None:
        fmt = "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s tenant_id=%(tenant_id)s trace_id=%(trace_id)s mode=%(mode)s %(message)s"
        super().__init__(fmt=fmt, datefmt="%Y-%m-%dT%H:%M:%S%z")

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = getattr(record, "request_id", "-")
        record.tenant_id = getattr(record, "tenant_id", "-")
        record.trace_id = getattr(record, "trace_id", "-")
        record.mode = getattr(record, "mode", "-")
        base = super().format(record)
        extras = []
        for key, value in record.__dict__.items():
            if key in self.STANDARD_ATTRS:
                continue
            extras.append(f"{key}={value}")
        if extras:
            return f"{base} {' '.join(extras)}"
        return base


class RequestLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: Any, kwargs: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        from app.modules.ops.security import SecurityUtils

        extra = kwargs.get("extra", {}).copy()
        context = get_request_context()
        extra.setdefault("request_id", context["request_id"])
        extra.setdefault("tenant_id", context["tenant_id"])
        extra.setdefault("trace_id", context["trace_id"])
        extra.setdefault("parent_trace_id", context["parent_trace_id"])
        extra.setdefault("mode", context["mode"])

        # Sanitize sensitive data in extra fields
        for key, value in list(extra.items()):
            if SecurityUtils._is_sensitive(key):
                extra[key] = SecurityUtils.mask_value(value, key)

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> RequestLoggerAdapter:
    return RequestLoggerAdapter(logging.getLogger(name), {})


def configure_logging(level: str | int = "INFO") -> None:
    if isinstance(level, str):
        level_value = getattr(logging, level.upper(), logging.INFO)
    else:
        level_value = level
    formatter = StructuredFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    if not getattr(root, "_structured_logging_initialized", False):
        root.handlers.clear()
        root.addHandler(handler)
        root.addHandler(file_handler)
        root._structured_logging_initialized = True
    else:
        for h in root.handlers:
            h.setFormatter(formatter)
    root.setLevel(level_value)

    # reduce noisy SSE heartbeat logs
    logging.getLogger("sse_starlette.sse").setLevel(logging.INFO)
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    # keep hot-reload logs readable by default (override with SQLALCHEMY_LOG_LEVEL=INFO/DEBUG)
    sqlalchemy_level = os.getenv("SQLALCHEMY_LOG_LEVEL", "WARNING").upper()
    logging.getLogger("sqlalchemy.engine").setLevel(
        getattr(logging, sqlalchemy_level, logging.WARNING)
    )
    logging.getLogger("sqlalchemy.pool").setLevel(
        getattr(logging, sqlalchemy_level, logging.WARNING)
    )
