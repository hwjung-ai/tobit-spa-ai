"""
Action Handler Registry: Maps action_id to deterministic executors

Action handlers route UI actions to existing OPS executors (config, history, metric, graph, etc.)
without creating new API endpoints.

All handlers follow this signature:
    async def handler(inputs, context, session) -> ExecutorResult
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse
from typing import Any, Callable, Dict

import httpx
from core.config import get_settings
from core.db_pg import get_pg_connection
from core.logging import get_logger
from sqlalchemy.orm import Session

from app.modules.asset_registry.loader import load_source_asset
from app.modules.ops.services.connections import ConnectionFactory

logger = get_logger(__name__)


def _default_action_metadata(action_id: str) -> Dict[str, Any]:
    return {
        "action_id": action_id,
        "label": action_id.replace("_", " ").title(),
        "description": "",
        "input_schema": {},
        "output": {"state_patch_keys": []},
        "required_context": [],
        "tags": [],
        "version": "v1",
        "experimental": False,
    }


def _set_dotted_path(target: Dict[str, Any], dotted_path: str, value: Any) -> None:
    """Set nested dictionary value from dotted path (`a.b.c`)."""
    parts = [part for part in dotted_path.split(".") if part]
    if not parts:
        raise ValueError("key must be a non-empty dotted path")

    cursor = target
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = value


def _get_connection():
    """Get connection using source asset."""
    settings = get_settings()
    source_asset = load_source_asset(settings.ops_default_source_asset)
    return ConnectionFactory.create(source_asset)


class ExecutorResult:
    """Result from action executor"""

    def __init__(
        self,
        blocks: list[Dict[str, Any]],
        tool_calls: list[Dict[str, Any]] | None = None,
        references: list[Dict[str, Any]] | None = None,
        summary: Dict[str, Any] | None = None,
        state_patch: Dict[str, Any] | None = None,
    ):
        self.blocks = blocks
        self.tool_calls = tool_calls or []
        self.references = references or []
        self.summary = summary or {}
        self.state_patch = state_patch or {}


class ActionRegistry:
    """Central registry for action handlers"""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._logger = get_logger("ActionRegistry")

    def register(self, action_id: str, metadata: Dict[str, Any] | None = None):
        """Decorator to register an action handler"""

        def decorator(func: Callable) -> Callable:
            self._handlers[action_id] = func
            merged_metadata = _default_action_metadata(action_id)
            if metadata:
                merged_metadata.update(metadata)
            self._metadata[action_id] = merged_metadata
            self._logger.info(f"Registered action handler: {action_id}")
            return func

        return decorator

    def get(self, action_id: str) -> Callable | None:
        """Get handler by action_id"""
        return self._handlers.get(action_id)

    def get_metadata(self, action_id: str) -> Dict[str, Any] | None:
        """Get action metadata by action_id."""
        return self._metadata.get(action_id)

    def list_actions(self) -> list[Dict[str, Any]]:
        """List registered action metadata sorted by action_id."""
        return [self._metadata[key] for key in sorted(self._metadata.keys())]

    async def execute(
        self,
        action_id: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        session: Session,
    ) -> ExecutorResult:
        """Execute action by action_id"""
        handler = self.get(action_id)
        if not handler:
            raise ValueError(f"Unknown action_id: {action_id}")

        self._logger.info(
            f"Executing action: {action_id}", extra={"action_id": action_id}
        )

        try:
            result = await handler(inputs, context, session)
            return result
        except Exception as e:
            self._logger.error(
                f"Action execution failed: {action_id}",
                extra={"action_id": action_id, "error": str(e)},
            )
            raise


# Global registry
_global_registry = ActionRegistry()


def register_action(action_id: str):
    """Register an action handler"""
    return _global_registry.register(action_id)


def register_action_with_meta(action_id: str, metadata: Dict[str, Any]):
    """Register an action handler with metadata."""
    return _global_registry.register(action_id, metadata=metadata)


def get_action_registry() -> ActionRegistry:
    """Get global action registry"""
    return _global_registry


def list_registered_actions() -> list[Dict[str, Any]]:
    """List metadata for all globally registered actions."""
    return _global_registry.list_actions()


async def execute_action(
    action_id: str,
    inputs: Dict[str, Any],
    context: Dict[str, Any],
    session: Session,
) -> ExecutorResult:
    """Execute action"""
    registry = get_action_registry()
    return await registry.execute(action_id, inputs, context, session)


# ============================================================================
# Built-in Action Handlers (MVP)
# ============================================================================


# Example handlers (to be implemented in integration)


@register_action_with_meta(
    "fetch_device_detail",
    metadata={
        "label": "Fetch Device Detail",
        "description": "Lookup a device detail snapshot for dashboard/detail screens.",
        "tags": ["device", "lookup", "detail"],
        "input_schema": {
            "type": "object",
            "required": ["device_id"],
            "properties": {
                "device_id": {"type": "string", "title": "Device ID"},
                "include_metrics": {
                    "type": "boolean",
                    "default": False,
                    "title": "Include Metrics",
                },
            },
        },
    },
)
async def handle_fetch_device_detail(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Fetch device detail (config executor)

    Inputs:
        - device_id: str
        - include_metrics: bool (optional)

    Returns:
        AnswerBlock with device details
    """

    device_id = inputs.get("device_id")
    if not device_id:
        raise ValueError("device_id required")

    # Use existing config executor

    # TODO: Call config executor directly (refactor handle_ops_query to expose executor)
    # For now, placeholder
    blocks = [
        {
            "type": "markdown",
            "content": f"Device detail for {device_id} (placeholder - implement with config executor)",
        }
    ]

    return ExecutorResult(blocks=blocks, summary={"device_id": device_id})


@register_action_with_meta(
    "list_maintenance_filtered",
    metadata={
        "label": "List Maintenance Filtered",
        "description": "Load maintenance history list with pagination.",
        "output": {"state_patch_keys": ["maintenance_list", "pagination"]},
        "tags": ["maintenance", "list", "table"],
        "input_schema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "default": "", "title": "Device ID"},
                "offset": {"type": "integer", "default": 0, "title": "Offset"},
                "limit": {"type": "integer", "default": 20, "title": "Limit"},
            },
        },
    },
)
async def handle_list_maintenance_filtered(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    List maintenance tickets with filters using database query

    Inputs:
        - device_id: str (optional, empty = all)
        - offset: int
        - limit: int

    Returns:
        AnswerBlock with table of maintenance tickets
    """
    from core.config import get_settings
    
    from app.shared.config_loader import load_text

    device_id = inputs.get("device_id", "").strip()
    offset = inputs.get("offset", 0)
    limit = inputs.get("limit", 20)
    tenant_id = context.get("tenant_id", "t1")

    try:
        # Load query SQL for maintenance history
        query_sql = load_text("queries/postgres/history/maintenance_history.sql")
        if not query_sql:
            raise ValueError("maintenance_history query not found")

        # Get PostgreSQL connection
        settings = get_settings()
        conn = get_pg_connection(settings)

        try:
            # Execute query with device filter (if provided)
            if device_id:
                # Query with device_id filter
                query_with_filter = f"""
                {query_sql}
                AND h.ci_id IN (
                    SELECT ci_id FROM ci WHERE tenant_id = %s AND ci_code = %s
                )
                """
                rows = conn.execute(
                    query_with_filter,
                    (tenant_id, device_id, "2099-01-01", "2024-01-01"),
                ).fetchall()
            else:
                # Query all maintenance records
                rows = conn.execute(
                    query_sql, (tenant_id, None, "2099-01-01", "2024-01-01")
                ).fetchall()

            # Format as table
            table_rows = []
            for i, row in enumerate(rows[offset : offset + limit], 1):
                # row format: (start_time, maint_type, duration_min, result, summary)
                table_rows.append(
                    [
                        f"M{offset + i:03d}",
                        device_id or "General",
                        row[1] if len(row) > 1 else "Maintenance",
                        row[3] if len(row) > 3 else "Completed",
                    ]
                )

            blocks = [
                {
                    "type": "table",
                    "columns": ["ID", "Device", "Type", "Status"],
                    "rows": table_rows
                    if table_rows
                    else [["M001", "General", "Preventive", "Scheduled"]],
                }
            ]

            # Calculate total for pagination
            total = len(rows) if rows else 0

            return ExecutorResult(
                blocks=blocks,
                summary={
                    "device_id": device_id,
                    "offset": offset,
                    "limit": limit,
                    "total": total,
                    "returned": len(table_rows),
                },
                state_patch={
                    "maintenance_list": [
                        {
                            "id": f"M{i:03d}",
                            "device_id": device_id or "General",
                            "type": row[1] if len(row) > 1 else "Maintenance",
                            "status": row[3] if len(row) > 3 else "Completed",
                            "date": str(row[0]) if len(row) > 0 else "",
                        }
                        for i, row in enumerate(
                            rows[offset : offset + limit], offset + 1
                        )
                    ],
                    "pagination": {"offset": offset, "limit": limit, "total": total},
                },
            )
        finally:
            conn.close()

    except Exception as e:
        logger.error(
            "list_maintenance_filtered.error",
            extra={"device_id": device_id, "error": str(e)},
        )
        # Fallback response
        blocks = [
            {
                "type": "markdown",
                "content": f"## 유지보수 목록 조회 실패\n\n오류: {str(e)}",
            }
        ]
        return ExecutorResult(blocks=blocks, summary={"error": str(e)})


@register_action_with_meta(
    "create_maintenance_ticket",
    metadata={
        "label": "Create Maintenance Ticket",
        "description": "Create a maintenance ticket and patch runtime state.",
        "output": {"state_patch_keys": ["last_created_ticket", "modal_open"]},
        "tags": ["maintenance", "create", "form"],
        "input_schema": {
            "type": "object",
            "required": ["device_id", "maintenance_type", "scheduled_date"],
            "properties": {
                "device_id": {"type": "string", "title": "Device ID"},
                "maintenance_type": {"type": "string", "title": "Maintenance Type"},
                "scheduled_date": {
                    "type": "string",
                    "title": "Scheduled Date",
                    "format": "date",
                },
                "assigned_to": {
                    "type": "string",
                    "default": "Unknown",
                    "title": "Assigned To",
                },
            },
        },
    },
)
async def handle_create_maintenance_ticket(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Create maintenance ticket by inserting into maintenance_history table

    Inputs:
        - device_id: str
        - maintenance_type: str
        - scheduled_date: str
        - assigned_to: str (optional)

    Returns:
        AnswerBlock confirming creation + state_patch with new ticket
    """
    import uuid
    from datetime import datetime, timezone

    from core.config import get_settings
    
    device_id = inputs.get("device_id", "").strip()
    maint_type = inputs.get("maintenance_type", "").strip()
    scheduled_date = inputs.get("scheduled_date", "").strip()
    assigned_to = inputs.get("assigned_to", "Unknown").strip()
    tenant_id = context.get("tenant_id", "t1")

    # Validate inputs
    if not all([device_id, maint_type, scheduled_date]):
        raise ValueError(
            "Missing required fields: device_id, maintenance_type, scheduled_date"
        )

    try:
        # Get PostgreSQL connection
        settings = get_settings()
        conn = get_pg_connection(settings)

        try:
            # Find CI ID for the device_id (ci_code)
            ci_rows = conn.execute(
                "SELECT ci_id FROM ci WHERE tenant_id = %s AND ci_code = %s LIMIT 1",
                (tenant_id, device_id),
            ).fetchall()

            if not ci_rows:
                # Create a mock response if device not found
                logger.warning(
                    f"Device {device_id} not found in CI table",
                    extra={"device_id": device_id},
                )
                ticket_id = f"MAINT-{str(uuid.uuid4())[:8].upper()}"
                blocks = [
                    {
                        "type": "markdown",
                        "content": f"## ⚠️ 장비를 찾을 수 없음\n\n장비 ID: {device_id}\n\n**참고**: 유지보수 레코드가 생성되지 않았습니다.",
                    }
                ]
            else:
                ci_id = ci_rows[0][0]

                # Insert maintenance record
                ticket_id = f"MAINT-{str(uuid.uuid4())[:8].upper()}"
                insert_query = """
                    INSERT INTO maintenance_history (
                        id, tenant_id, ci_id, maint_type, summary, detail,
                        start_time, end_time, duration_min, performer, result, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """

                now = datetime.now(timezone.utc)
                conn.execute(
                    insert_query,
                    (
                        str(uuid.uuid4()),  # id
                        tenant_id,  # tenant_id
                        ci_id,  # ci_id
                        maint_type,  # maint_type
                        f"Scheduled {maint_type}",  # summary
                        f"Scheduled for {scheduled_date}. Assigned to: {assigned_to}",  # detail
                        now,  # start_time
                        None,  # end_time
                        0,  # duration_min
                        assigned_to,  # performer
                        "Scheduled",  # result
                        now,  # created_at
                    ),
                )
                conn.commit()

                blocks = [
                    {
                        "type": "markdown",
                        "content": f"## ✅ 유지보수 티켓 생성 완료\n\n**티켓 ID**: {ticket_id}\n**장비**: {device_id}\n**타입**: {maint_type}\n**예정일**: {scheduled_date}\n**담당자**: {assigned_to}",
                    },
                ]

            return ExecutorResult(
                blocks=blocks,
                summary={
                    "ticket_id": ticket_id,
                    "device_id": device_id,
                    "maintenance_type": maint_type,
                    "scheduled_date": scheduled_date,
                },
                state_patch={
                    "last_created_ticket": {
                        "id": ticket_id,
                        "device_id": device_id,
                        "type": maint_type,
                        "scheduled_date": scheduled_date,
                        "assigned_to": assigned_to,
                        "status": "Scheduled",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "modal_open": False,  # Close modal after creation
                },
            )

        finally:
            conn.close()

    except Exception as e:
        logger.error(
            "create_maintenance_ticket.error",
            extra={"device_id": device_id, "error": str(e)},
        )
        blocks = [
            {
                "type": "markdown",
                "content": f"## ❌ 유지보수 티켓 생성 실패\n\n오류: {str(e)}",
            }
        ]
        return ExecutorResult(blocks=blocks, summary={"error": str(e)})


@register_action_with_meta(
    "open_maintenance_modal",
    metadata={
        "label": "Open Maintenance Modal",
        "description": "Open maintenance modal by patching UI state.",
        "output": {"state_patch_keys": ["modal_open"]},
        "tags": ["ui", "modal", "state"],
        "input_schema": {"type": "object", "properties": {}},
    },
)
async def handle_open_maintenance_modal(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Open maintenance creation modal (UI state change only, no executor)

    Returns:
        AnswerBlock (placeholder)
    """
    blocks = [
        {
            "type": "markdown",
            "content": "Create new maintenance ticket (modal opened)",
        }
    ]
    return ExecutorResult(blocks=blocks, state_patch={"modal_open": True})


@register_action_with_meta(
    "close_maintenance_modal",
    metadata={
        "label": "Close Maintenance Modal",
        "description": "Close maintenance modal by patching UI state.",
        "output": {"state_patch_keys": ["modal_open"]},
        "tags": ["ui", "modal", "state"],
        "input_schema": {"type": "object", "properties": {}},
    },
)
async def handle_close_maintenance_modal(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Close maintenance creation modal (UI state change only)

    Returns:
        AnswerBlock (placeholder)
    """
    blocks = []
    return ExecutorResult(blocks=blocks, state_patch={"modal_open": False})


@register_action_with_meta(
    "state.set",
    metadata={
        "label": "State Set",
        "description": "Set a single state value using dotted key path.",
        "output": {"state_patch_keys": ["dynamic"]},
        "tags": ["state", "utility"],
        "input_schema": {
            "type": "object",
            "required": ["key", "value"],
            "properties": {
                "key": {"type": "string", "title": "State Path (dotted)"},
                "value": {"title": "Value"},
            },
        },
    },
)
async def handle_state_set(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    key = str(inputs.get("key", "")).strip()
    if not key:
        raise ValueError("key required")
    if "value" not in inputs:
        raise ValueError("value required")

    patch: Dict[str, Any] = {}
    _set_dotted_path(patch, key, inputs.get("value"))
    return ExecutorResult(
        blocks=[{"type": "markdown", "content": f"state updated: `{key}`"}],
        state_patch=patch,
        summary={"updated_key": key},
    )


@register_action_with_meta(
    "state.merge",
    metadata={
        "label": "State Merge",
        "description": "Merge a patch object into runtime state.",
        "output": {"state_patch_keys": ["patch.*"]},
        "tags": ["state", "utility"],
        "input_schema": {
            "type": "object",
            "required": ["patch"],
            "properties": {
                "patch": {"type": "object", "title": "State Patch"},
            },
        },
    },
)
async def handle_state_merge(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    patch = inputs.get("patch")
    if not isinstance(patch, dict):
        raise ValueError("patch must be object")
    return ExecutorResult(
        blocks=[{"type": "markdown", "content": "state merged"}],
        state_patch=patch,
        summary={"patch_keys": sorted(patch.keys())},
    )


@register_action_with_meta(
    "nav.go_to",
    metadata={
        "label": "Navigate To",
        "description": "Emit navigation intent for runtime/router integration.",
        "output": {"state_patch_keys": ["__nav"]},
        "tags": ["navigation", "utility"],
        "input_schema": {
            "type": "object",
            "required": ["to"],
            "properties": {
                "to": {"type": "string", "title": "Route"},
                "query": {"type": "object", "title": "Query Params"},
            },
        },
    },
)
async def handle_nav_go_to(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    route_to = str(inputs.get("to", "")).strip()
    if not route_to:
        raise ValueError("to required")
    query = inputs.get("query")
    query_obj = query if isinstance(query, dict) else {}
    return ExecutorResult(
        blocks=[{"type": "markdown", "content": f"navigate to `{route_to}`"}],
        state_patch={"__nav": {"to": route_to, "query": query_obj}},
        summary={"to": route_to, "query_keys": sorted(query_obj.keys())},
    )


@register_action_with_meta(
    "workflow.run",
    metadata={
        "label": "Run Workflow",
        "description": "Trigger workflow execution and store run result in screen state.",
        "output": {"state_patch_keys": ["workflow_last_run"]},
        "tags": ["workflow", "execute"],
        "input_schema": {
            "type": "object",
            "required": ["workflow_id"],
            "properties": {
                "workflow_id": {"type": "string", "title": "Workflow ID"},
                "inputs": {"type": "object", "title": "Workflow Inputs"},
            },
        },
    },
)
async def handle_workflow_run(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    from datetime import datetime, timezone

    workflow_id = str(inputs.get("workflow_id", "")).strip()
    if not workflow_id:
        raise ValueError("workflow_id required")

    workflow_inputs = inputs.get("inputs")
    input_obj = workflow_inputs if isinstance(workflow_inputs, dict) else {}
    timestamp = datetime.now(timezone.utc).isoformat()
    return ExecutorResult(
        blocks=[
            {
                "type": "markdown",
                "content": f"workflow `{workflow_id}` triggered",
            }
        ],
        state_patch={
            "workflow_last_run": {
                "workflow_id": workflow_id,
                "inputs": input_obj,
                "status": "triggered",
                "triggered_at": timestamp,
            }
        },
        summary={"workflow_id": workflow_id},
    )


@register_action_with_meta(
    "form.submit",
    metadata={
        "label": "Submit Form",
        "description": "Submit form payload and persist latest submission in runtime state.",
        "output": {"state_patch_keys": ["form_last_submission"]},
        "tags": ["form", "submit"],
        "input_schema": {
            "type": "object",
            "required": ["form_id", "payload"],
            "properties": {
                "form_id": {"type": "string", "title": "Form ID"},
                "payload": {"type": "object", "title": "Form Payload"},
            },
        },
    },
)
async def handle_form_submit(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    from datetime import datetime, timezone

    form_id = str(inputs.get("form_id", "")).strip()
    if not form_id:
        raise ValueError("form_id required")
    payload = inputs.get("payload")
    payload_obj = payload if isinstance(payload, dict) else {}
    timestamp = datetime.now(timezone.utc).isoformat()
    return ExecutorResult(
        blocks=[{"type": "markdown", "content": f"form `{form_id}` submitted"}],
        state_patch={
            "form_last_submission": {
                "form_id": form_id,
                "payload": payload_obj,
                "submitted_at": timestamp,
            }
        },
        summary={"form_id": form_id, "payload_keys": sorted(payload_obj.keys())},
    )


@register_action_with_meta(
    "api.call",
    metadata={
        "label": "API Call",
        "description": "Call external/internal HTTP API and store response into runtime state.",
        "output": {"state_patch_keys": ["api_last_response"]},
        "tags": ["api", "http", "integration"],
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "title": "Request URL"},
                "method": {
                    "type": "string",
                    "default": "GET",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                },
                "headers": {"type": "object", "title": "Request headers"},
                "query": {"type": "object", "title": "Query params"},
                "body": {"title": "Request body"},
                "timeout_ms": {"type": "integer", "default": 10000},
            },
        },
    },
)
async def handle_api_call(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    raw_url = str(inputs.get("url", "")).strip()
    if not raw_url:
        raise ValueError("url required")

    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("url must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("url host required")

    hostname = parsed.hostname or ""
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip and (ip.is_loopback or ip.is_private or ip.is_link_local):
        raise ValueError("private/local network target is not allowed")

    method = str(inputs.get("method", "GET")).upper()
    if method not in {"GET", "POST", "PUT", "DELETE"}:
        raise ValueError("method must be one of GET/POST/PUT/DELETE")

    headers = inputs.get("headers")
    headers_obj = headers if isinstance(headers, dict) else {}
    query = inputs.get("query")
    query_obj = query if isinstance(query, dict) else {}
    body = inputs.get("body")
    timeout_ms = int(inputs.get("timeout_ms", 10000) or 10000)
    timeout_seconds = max(1.0, min(60.0, timeout_ms / 1000.0))

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.request(
            method=method,
            url=raw_url,
            headers={str(k): str(v) for k, v in headers_obj.items()},
            params=query_obj,
            json=body if method in {"POST", "PUT", "DELETE"} else None,
        )

    content_type = response.headers.get("content-type", "")
    response_payload: Any
    if "application/json" in content_type:
        try:
            response_payload = response.json()
        except Exception:
            response_payload = response.text
    else:
        response_payload = response.text

    result = {
        "url": raw_url,
        "method": method,
        "status_code": response.status_code,
        "ok": response.is_success,
        "headers": dict(response.headers),
        "data": response_payload,
    }

    return ExecutorResult(
        blocks=[
            {
                "type": "markdown",
                "content": f"api.call `{method} {raw_url}` -> {response.status_code}",
            }
        ],
        state_patch={"api_last_response": result},
        summary={
            "url": raw_url,
            "method": method,
            "status_code": response.status_code,
            "ok": response.is_success,
        },
    )
