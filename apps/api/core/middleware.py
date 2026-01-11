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
        request.state.request_id = request_id
        request.state.tenant_id = tenant_id
        set_request_context(request_id, tenant_id, mode="ci")
        try:
            response: Response = await call_next(request)
        finally:
            clear_request_context()
        response.headers["X-Request-ID"] = request_id
        return response
