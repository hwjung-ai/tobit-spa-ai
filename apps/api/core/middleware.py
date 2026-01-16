from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.api.core.logging import clear_request_context, set_request_context


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        tenant_id = request.headers.get("x-tenant-id") or "t1"
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        parent_trace_id = request.headers.get("x-parent-trace-id") or ""
        request.state.request_id = request_id
        request.state.tenant_id = tenant_id
        request.state.trace_id = trace_id
        request.state.parent_trace_id = parent_trace_id
        set_request_context(request_id, tenant_id, mode="ci", trace_id=trace_id, parent_trace_id=parent_trace_id)
        try:
            response: Response = await call_next(request)
        finally:
            clear_request_context()
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        if parent_trace_id:
            response.headers["X-Parent-Trace-ID"] = parent_trace_id
        return response
