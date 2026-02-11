from __future__ import annotations

from uuid import uuid4

from app.modules.inspector.asset_context import reset_asset_context
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.api.core.logging import (
    clear_request_context,
    get_logger,
    get_request_context,
    set_request_context,
)
from core.config import get_settings

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        request_id = request.headers.get("x-request-id") or str(uuid4())
        tenant_id = request.headers.get("x-tenant-id") or settings.default_tenant_id
        # trace_id: 클라이언트에서 전달하거나 새로 생성. 하이픈 포함 표준 UUID 형식 사용
        provided_trace_id = request.headers.get("x-trace-id")
        if provided_trace_id:
            # 하이픈이 없는 32자 hex 형식인 경우, 표준 UUID 형식으로 변환
            if "-" not in provided_trace_id and len(provided_trace_id) == 32:
                # xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx 형식으로 변환
                trace_id = f"{provided_trace_id[0:8]}-{provided_trace_id[8:12]}-{provided_trace_id[12:16]}-{provided_trace_id[16:20]}-{provided_trace_id[20:32]}"
                print(f"[MIDDLEWARE] Converted trace_id: {provided_trace_id} -> {trace_id}")
            else:
                trace_id = provided_trace_id
                print(f"[MIDDLEWARE] Using trace_id: {trace_id}")
        else:
            trace_id = str(uuid4())
            print(f"[MIDDLEWARE] Generated trace_id: {trace_id}")
        parent_trace_id = request.headers.get("x-parent-trace-id") or ""
        request.state.request_id = request_id
        request.state.tenant_id = tenant_id
        request.state.trace_id = trace_id
        request.state.parent_trace_id = parent_trace_id
        reset_asset_context()
        set_request_context(
            request_id,
            tenant_id,
            mode="ci",
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
        )
        # Verify context was set correctly
        ctx_check = get_request_context()
        print(f"[MIDDLEWARE] Context set, trace_id={ctx_check.get('trace_id')}, request_id={ctx_check.get('request_id')}")
        try:
            response: Response = await call_next(request)
        finally:
            clear_request_context()
            reset_asset_context()
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        if parent_trace_id:
            response.headers["X-Parent-Trace-ID"] = parent_trace_id
        return response
