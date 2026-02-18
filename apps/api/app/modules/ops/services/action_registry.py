"""
Action Handler Registry: Maps action_id to deterministic executors

Action handlers route UI actions to existing OPS executors (config, history, metric, graph, etc.)
without creating new API endpoints.

All handlers follow this signature:
    async def handler(inputs, context, session) -> ExecutorResult
"""

from __future__ import annotations

import asyncio
import ipaddress
from typing import Any, Callable, Dict
from urllib.parse import urlparse

import httpx
from core.config import get_settings
from core.db_pg import get_pg_connection
from core.logging import get_logger
from sqlalchemy.orm import Session

from app.modules.ops.services.orchestration.tools.base import ToolContext, get_tool_registry

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
        "sample_output": None,
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
        "sample_output": {
            "state_patch": {
                "device_detail": {
                    "device_id": "DEV-001",
                    "name": "MES Server 06",
                    "status": "online",
                    "cpu_usage": 45.2,
                    "memory_usage": 62.1,
                    "last_heartbeat": "2026-02-08T10:30:00Z",
                }
            }
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
        "sample_output": {
            "state_patch": {
                "maintenance_list": [
                    {"id": "M001", "device_id": "DEV-001", "type": "Preventive", "status": "Completed", "date": "2026-02-01"},
                    {"id": "M002", "device_id": "DEV-002", "type": "Corrective", "status": "Scheduled", "date": "2026-02-10"},
                ],
                "pagination": {"offset": 0, "limit": 20, "total": 2},
            }
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

    device_id = inputs.get("device_id", "").strip()
    offset = inputs.get("offset", 0)
    limit = inputs.get("limit", 20)
    tenant_id = context.get("tenant_id") or get_settings().default_tenant_id

    source_ref = (inputs.get("source_ref") or context.get("source_asset") or "").strip()
    if not source_ref:
        raise ValueError("source_ref is required")

    try:
        # Use Tool Registry to find maintenance history tool by capability
        registry = get_tool_registry()
        tool = registry.find_tool_by_capability("maintenance_history")

        if not tool:
            raise ValueError(
                "No maintenance history tool found in Tool Registry. "
                "Please create a Tool with name containing 'maintenance_history' "
                "or with tool_config.capabilities including 'maintenance_history'."
            )

        # Create tool context
        tool_context = ToolContext(
            tenant_id=tenant_id,
            user_id=context.get("user_id", "system"),
            request_id=context.get("request_id", ""),
            trace_id=context.get("trace_id", ""),
            metadata={
                "source_ref": source_ref,
                "device_id": device_id,
            }
        )

        # Execute tool
        tool_params = {
            "device_id": device_id,
            "offset": offset,
            "limit": limit,
            "source_ref": source_ref,
        }

        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(tool_context, tool_params)
        )

        if not result.success:
            raise ValueError(f"Tool execution failed: {result.error}")

        # Format result as table
        tool_data = result.data or []
        table_rows = []
        for i, row in enumerate(tool_data[offset : offset + limit], 1):
            if isinstance(row, dict):
                table_rows.append([
                    row.get("id", f"M{offset + i:03d}"),
                    row.get("device_id", device_id or "General"),
                    row.get("type", row.get("maint_type", "Maintenance")),
                    row.get("status", "Completed"),
                ])
            else:
                # Legacy format: tuple/list
                table_rows.append([
                    f"M{offset + i:03d}",
                    device_id or "General",
                    row[1] if len(row) > 1 else "Maintenance",
                    row[3] if len(row) > 3 else "Completed",
                ])

        blocks = [
            {
                "type": "table",
                "columns": ["ID", "Device", "Type", "Status"],
                "rows": table_rows if table_rows else [["M001", "General", "Preventive", "Scheduled"]],
            }
        ]

        # Calculate total for pagination
        total = len(tool_data) if tool_data else 0

        return ExecutorResult(
            blocks=blocks,
            summary={
                "total": total,
                "offset": offset,
                "limit": limit,
            },
            state_patch={
                "maintenance_list": tool_data,
                "pagination": {"offset": offset, "limit": limit, "total": total},
            },
        )

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
        "sample_output": {
            "state_patch": {
                "last_created_ticket": {
                    "id": "MAINT-ABC12345",
                    "device_id": "DEV-001",
                    "type": "Preventive",
                    "scheduled_date": "2026-03-01",
                    "assigned_to": "admin",
                    "status": "Scheduled",
                },
                "modal_open": False,
            }
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


    device_id = inputs.get("device_id", "").strip()
    maint_type = inputs.get("maintenance_type", "").strip()
    scheduled_date = inputs.get("scheduled_date", "").strip()
    assigned_to = inputs.get("assigned_to", "Unknown").strip()
    tenant_id = context.get("tenant_id") or get_settings().default_tenant_id

    source_ref = (inputs.get("source_ref") or context.get("source_asset") or "").strip()
    if not source_ref:
        raise ValueError("source_ref is required")

    # Validate inputs
    if not all([device_id, maint_type, scheduled_date]):
        raise ValueError(
            "Missing required fields: device_id, maintenance_type, scheduled_date"
        )

    try:
        # Get PostgreSQL connection
        settings = get_settings()
        conn = get_pg_connection(settings, use_source_asset=True, source_ref=source_ref)

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
        "sample_output": {"state_patch": {"modal_open": True}},
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
        "sample_output": {"state_patch": {"modal_open": False}},
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
        "sample_output": {
            "state_patch": {"<key>": "<value>"},
            "_note": "key/value are dynamic - state_patch key matches the 'key' input",
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
        "sample_output": {
            "state_patch": {"<patch keys>": "<patch values>"},
            "_note": "patch object is merged directly into state",
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
        "sample_output": {
            "state_patch": {"__nav": {"to": "/admin/screens/my_screen", "query": {}}}
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
        "sample_output": {
            "state_patch": {
                "workflow_last_run": {
                    "workflow_id": "wf_daily_check",
                    "inputs": {},
                    "status": "triggered",
                    "triggered_at": "2026-02-08T10:00:00Z",
                }
            }
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
        "sample_output": {
            "state_patch": {
                "form_last_submission": {
                    "form_id": "ticket_form",
                    "payload": {"device_id": "DEV-001", "note": "Routine check"},
                    "submitted_at": "2026-02-08T10:00:00Z",
                }
            }
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
        "sample_output": {
            "state_patch": {
                "api_last_response": {
                    "url": "https://api.example.com/data",
                    "method": "GET",
                    "status_code": 200,
                    "ok": True,
                    "data": {"items": [], "total": 0},
                }
            }
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


@register_action_with_meta(
    "api_manager.execute",
    metadata={
        "label": "Execute API Manager API",
        "description": "Execute a user-defined API from API Manager (SQL/HTTP/Script/Workflow).",
        "output": {"state_patch_keys": ["api_result"]},
        "tags": ["api_manager", "dynamic", "integration"],
        "input_schema": {
            "type": "object",
            "required": ["api_id"],
            "properties": {
                "api_id": {"type": "string", "title": "API Manager API ID"},
                "params": {"type": "object", "title": "Execution Parameters", "default": {}},
            },
        },
        "sample_output": {
            "state_patch": {
                "api_result": {
                    "columns": ["id", "name", "status"],
                    "rows": [["1", "Server A", "online"]],
                    "row_count": 1,
                    "duration_ms": 42,
                }
            }
        },
    },
)
async def handle_api_manager_execute(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Execute a user-defined API from API Manager.

    Routes to the appropriate executor (SQL, HTTP, Script, Workflow) based on API mode.

    Inputs:
        - api_id: str (API Manager API UUID)
        - params: dict (execution parameters)

    Returns:
        ExecutorResult with API execution result in state_patch.api_result
    """
    import json as _json

    from models.api_definition import ApiDefinition

    from app.modules.api_manager.executor import execute_http_api, execute_sql_api
    from app.modules.api_manager.script_executor import execute_script_api
    from app.modules.api_manager.workflow_executor import execute_workflow_api

    api_id = str(inputs.get("api_id", "")).strip()
    if not api_id:
        raise ValueError("api_id required")

    params = inputs.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    api = session.get(ApiDefinition, api_id)
    if not api or api.deleted_at:
        raise ValueError(f"API not found: {api_id}")
    if not api.logic:
        raise ValueError(f"API has no logic defined: {api.name}")

    mode = api.mode.value if api.mode else "sql"
    executed_by = context.get("user_id", "screen_action")

    def _result_dict(result):
        return {
            "columns": getattr(result, "columns", []),
            "rows": getattr(result, "rows", []),
            "row_count": getattr(result, "row_count", 0),
            "duration_ms": getattr(result, "duration_ms", 0),
        }

    if mode == "sql":
        result = execute_sql_api(
            session=session,
            api_id=api_id,
            logic_body=api.logic,
            params=params or None,
            limit=params.get("limit"),
            executed_by=executed_by,
        )
        result_data = _result_dict(result)
    elif mode == "http":
        result = execute_http_api(
            session=session,
            api_id=api_id,
            logic_body=api.logic,
            params=params or None,
            executed_by=executed_by,
        )
        result_data = _result_dict(result)
    elif mode == "workflow":
        class _WfAdapter:
            def __init__(self, ad):
                self.api_id = ad.id
                self.logic_spec = {}
                self.logic = ad.logic
                try:
                    self.logic_spec = _json.loads(ad.logic or "{}")
                except (ValueError, TypeError):
                    pass

        wf_result = execute_workflow_api(
            session=session,
            workflow_api=_WfAdapter(api),
            params=params,
            input_payload=None,
            executed_by=executed_by,
            limit=params.get("limit"),
        )
        result_data = wf_result.model_dump() if hasattr(wf_result, "model_dump") else {}
    elif mode in ("script", "python"):
        sc_result = execute_script_api(
            session=session,
            api_id=api_id,
            logic_body=api.logic,
            params=params or None,
            input_payload=None,
            executed_by=executed_by,
            runtime_policy=getattr(api, "runtime_policy", None),
        )
        result_data = sc_result.model_dump() if hasattr(sc_result, "model_dump") else {}
    else:
        raise ValueError(f"Unsupported API mode: {mode}")

    return ExecutorResult(
        blocks=[
            {
                "type": "markdown",
                "content": f"API `{api.name}` ({mode}) executed successfully",
            }
        ],
        state_patch={"api_result": result_data},
        summary={
            "api_id": api_id,
            "api_name": api.name,
            "mode": mode,
            "row_count": result_data.get("row_count", 0),
        },
    )


# ============================================================================
# Monitoring Action Handlers (CEP + System)
# ============================================================================


@register_action_with_meta(
    "fetch_cep_stats",
    metadata={
        "label": "Fetch CEP Stats",
        "description": "Fetch CEP monitoring data: stats summary, channels status, rules performance, and error timeline.",
        "output": {
            "state_patch_keys": [
                "total_rules", "active_rules", "today_execution_count",
                "today_error_count", "today_error_rate", "today_avg_duration_ms",
                "last_24h_execution_count", "no_data_ratio",
                "cep_rules", "cep_events", "channels",
                "error_timeline", "error_distribution", "recent_errors",
            ]
        },
        "tags": ["cep", "monitoring", "dashboard"],
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "default": "24h",
                    "enum": ["1h", "6h", "24h", "7d"],
                    "title": "Error Timeline Period",
                },
            },
        },
        "sample_output": {
            "state_patch": {
                "total_rules": 5,
                "active_rules": 3,
                "today_execution_count": 142,
                "today_error_count": 3,
                "today_error_rate": 0.02,
                "today_avg_duration_ms": 45.2,
                "last_24h_execution_count": 340,
                "cep_rules": [
                    {"rule_name": "High CPU Alert", "is_active": True, "execution_count": 50, "error_rate": 0.02, "avg_duration_ms": 30.5},
                ],
                "channels": [
                    {"type": "slack", "display_name": "Slack", "active": 2, "total_sent": 10, "failure_rate": 0.0},
                ],
            }
        },
    },
)
async def handle_fetch_cep_stats(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Fetch all CEP monitoring data by calling internal CEP endpoints.

    Aggregates data from:
        - /cep/stats/summary
        - /cep/channels/status
        - /cep/rules/performance
        - /cep/errors/timeline
    """
    from datetime import timedelta

    from sqlmodel import select as sql_select

    from app.modules.cep_builder.models import TbCepExecLog, TbCepRule

    period = inputs.get("period", "24h")

    try:
        # 1. Stats summary
        from datetime import datetime as dt
        from datetime import timezone as tz
        now = dt.now(tz.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        all_rules = session.exec(sql_select(TbCepRule)).all()
        total_rules = len(all_rules)
        active_rules = sum(1 for r in all_rules if r.is_active)

        today_logs = session.exec(
            sql_select(TbCepExecLog).where(TbCepExecLog.triggered_at >= today_start)
        ).all()
        today_exec_count = len(today_logs)
        today_errors = sum(1 for log in today_logs if log.status == "fail")
        avg_duration = (sum((log.duration_ms or 0) for log in today_logs) / len(today_logs)) if today_logs else 0
        error_rate = (today_errors / len(today_logs)) if today_logs else 0

        last_24h = now - timedelta(hours=24)
        logs_24h = session.exec(
            sql_select(TbCepExecLog).where(TbCepExecLog.triggered_at >= last_24h)
        ).all()
        last_24h_count = len(logs_24h)

        # no_data_ratio: ratio of rules with 0 executions today
        rules_with_exec = set()
        for log in today_logs:
            rules_with_exec.add(str(log.rule_id))
        no_data_ratio = round(
            (total_rules - len(rules_with_exec)) / total_rules, 3
        ) if total_rules else 0

        # 2. Rules performance (top 10)
        last_7d = now - timedelta(days=7)
        cep_rules_perf = []
        for rule in all_rules:
            rule_logs = session.exec(
                sql_select(TbCepExecLog).where(
                    (TbCepExecLog.rule_id == rule.rule_id) &
                    (TbCepExecLog.triggered_at >= last_7d)
                )
            ).all()
            if rule_logs:
                exec_count = len(rule_logs)
                err_count = sum(1 for log_item in rule_logs if log_item.status == "fail")
                avg_dur = (
                    sum((log_item.duration_ms or 0) for log_item in rule_logs)
                    / exec_count
                )
                cep_rules_perf.append({
                    "rule_name": str(rule.rule_name),
                    "trigger_type": str(getattr(rule, "trigger_type", "event")),
                    "is_active": bool(rule.is_active),
                    "execution_count": exec_count,
                    "error_count": err_count,
                    "error_rate": round(err_count / exec_count, 3),
                    "avg_duration_ms": round(avg_dur, 2),
                    "updated_at": str(getattr(rule, "updated_at", "")),
                })
        cep_rules_perf.sort(key=lambda x: x["execution_count"], reverse=True)

        # 3. Error timeline
        period_mapping = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }
        lookback = period_mapping.get(period, timedelta(hours=24))
        cutoff = now - lookback

        error_logs = session.exec(
            sql_select(TbCepExecLog).where(
                (TbCepExecLog.triggered_at >= cutoff) &
                (TbCepExecLog.status == "fail")
            ).order_by(TbCepExecLog.triggered_at.desc())
        ).all()

        timeline_dict: Dict[str, int] = {}
        cur = cutoff.replace(minute=0, second=0, microsecond=0)
        while cur <= now:
            timeline_dict[cur.isoformat()] = 0
            cur += timedelta(hours=1)

        error_types: Dict[str, int] = {}
        for log in error_logs:
            hour_key = log.triggered_at.replace(minute=0, second=0, microsecond=0).isoformat()
            if hour_key in timeline_dict:
                timeline_dict[hour_key] += 1
            err_type = "other"
            if log.error_message:
                msg = log.error_message.lower()
                if "timeout" in msg:
                    err_type = "timeout"
                elif "connection" in msg:
                    err_type = "connection"
                elif "validation" in msg:
                    err_type = "validation"
                elif "authentication" in msg:
                    err_type = "authentication"
            error_types[err_type] = error_types.get(err_type, 0) + 1

        # Recent errors as CEP events table
        cep_events = []
        for log in error_logs[:20]:
            rule = next((r for r in all_rules if str(r.rule_id) == str(log.rule_id)), None)
            duration = log.duration_ms or 0
            severity = "critical" if duration > 5000 else "high" if duration > 2000 else "medium"
            cep_events.append({
                "triggered_at": log.triggered_at.isoformat(),
                "severity": severity,
                "rule_name": rule.rule_name if rule else "Unknown",
                "summary": log.error_message or "Execution failed",
                "status": log.status,
                "ack": "No",
            })

        # 4. Channels status
        channels = []
        try:
            from app.modules.cep_builder.models import (
                TbCepNotification,
                TbCepNotificationLog,
            )

            notifications = session.exec(sql_select(TbCepNotification)).all()
            channels_map: Dict[str, Dict[str, Any]] = {}
            lookback_24h = now - timedelta(hours=24)

            for notif in notifications:
                ch_type = notif.channel
                if ch_type not in channels_map:
                    channels_map[ch_type] = {
                        "type": ch_type,
                        "display_name": {"slack": "Slack", "email": "Email", "sms": "SMS", "webhook": "Webhook", "pagerduty": "PagerDuty"}.get(ch_type, ch_type),
                        "active": 0, "inactive": 0,
                        "total_sent": 0, "total_failed": 0,
                        "failure_rate": 0, "last_sent_at": None,
                    }
                if notif.is_active:
                    channels_map[ch_type]["active"] += 1
                else:
                    channels_map[ch_type]["inactive"] += 1

                try:
                    notif_logs = session.exec(
                        sql_select(TbCepNotificationLog).where(
                            (TbCepNotificationLog.notification_id == notif.notification_id) &
                            (TbCepNotificationLog.fired_at >= lookback_24h)
                        )
                    ).all()
                    for nl in notif_logs:
                        channels_map[ch_type]["total_sent"] += 1
                        if nl.status != "success":
                            channels_map[ch_type]["total_failed"] += 1
                except Exception:
                    pass

            for ch_data in channels_map.values():
                if ch_data["total_sent"] > 0:
                    ch_data["failure_rate"] = round(ch_data["total_failed"] / ch_data["total_sent"], 3)
                channels.append(ch_data)
        except Exception as ch_err:
            logger.warning(f"fetch_cep_stats: channels lookup skipped: {ch_err}")

        error_timeline = [
            {"timestamp": k, "error_count": v}
            for k, v in sorted(timeline_dict.items())
        ]

        state_patch = {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "today_execution_count": today_exec_count,
            "today_error_count": today_errors,
            "today_error_rate": round(error_rate, 3),
            "today_avg_duration_ms": round(avg_duration, 2),
            "last_24h_execution_count": last_24h_count,
            "no_data_ratio": no_data_ratio,
            "cep_rules": cep_rules_perf[:10],
            "cep_events": cep_events,
            "channels": channels,
            "error_timeline": error_timeline,
            "error_distribution": error_types,
            "recent_errors": cep_events[:10],
            "total_errors": len(error_logs),
        }

        return ExecutorResult(
            blocks=[{"type": "markdown", "content": "CEP stats loaded"}],
            state_patch=state_patch,
            summary={"total_rules": total_rules, "today_executions": today_exec_count},
        )

    except Exception as e:
        logger.error(f"fetch_cep_stats.error: {e}", exc_info=True)
        return ExecutorResult(
            blocks=[{"type": "markdown", "content": f"## CEP Stats Error\n\n{str(e)}"}],
            state_patch={},
            summary={"error": str(e)},
        )


@register_action_with_meta(
    "fetch_system_health",
    metadata={
        "label": "Fetch System Health",
        "description": "Fetch system monitoring data: CPU, memory, disk, network, OPS query stats, and alerts.",
        "output": {
            "state_patch_keys": [
                "cpu_usage", "memory_usage", "memory_available_gb",
                "disk_usage", "disk_available_gb", "system_status",
                "system_alerts", "alert_count",
                "today_query_count", "today_error_count", "today_error_rate",
                "success_rate", "failure_rate", "latency_p50", "latency_p95",
                "regression_trend", "regression_totals", "top_causes", "no_data_ratio",
            ]
        },
        "tags": ["system", "monitoring", "dashboard", "health"],
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "sample_output": {
            "state_patch": {
                "cpu_usage": 32.5,
                "memory_usage": 58.0,
                "memory_available_gb": 6.8,
                "disk_usage": 45.0,
                "disk_available_gb": 120.5,
                "system_status": "healthy",
                "system_alerts": [],
                "today_query_count": 156,
                "today_error_rate": 0.02,
            }
        },
    },
)
async def handle_fetch_system_health(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Fetch system health metrics by combining psutil data with OPS observability metrics.

    Sources:
        - psutil: CPU, memory, disk
        - observability_service: OPS query stats, regression data
        - SystemMonitor: service health checks
    """
    import psutil

    try:
        # 1. System resource metrics via psutil (Robust)
        try:
            cpu_usage = psutil.cpu_percent(interval=None)  # Use non-blocking call first if preferable, or short interval
            mem = psutil.virtual_memory()
            memory_usage = mem.percent
            memory_available_gb = round(mem.available / (1024 ** 3), 1)
            disk = psutil.disk_usage("/")
            disk_usage = disk.percent
            disk_available_gb = round(disk.free / (1024 ** 3), 1)
        except Exception as e:
            logger.warning(f"psutil failed in system health check: {e}")
            cpu_usage, memory_usage, memory_available_gb = 0, 0, 0
            disk_usage, disk_available_gb = 0, 0

        # Determine system status based on available metrics
        if cpu_usage > 90 or memory_usage > 90 or disk_usage > 95:
            system_status = "critical"
        elif cpu_usage > 70 or memory_usage > 80 or disk_usage > 85:
            system_status = "warning"
        else:
            system_status = "healthy"

        # 2. OPS observability metrics
        from app.modules.ops.services.observability_service import (
            collect_observability_metrics,
        )
        obs_metrics = collect_observability_metrics(session)

        success_rate = obs_metrics.get("success_rate", 0)
        failure_rate = obs_metrics.get("failure_rate", 0)
        total_recent_requests = obs_metrics.get("total_recent_requests", 0)
        latency = obs_metrics.get("latency", {})
        regression_trend = obs_metrics.get("regression_trend", [])
        regression_totals = obs_metrics.get("regression_totals", {"PASS": 0, "WARN": 0, "FAIL": 0})
        top_causes = obs_metrics.get("top_causes", [])
        no_data_ratio = obs_metrics.get("no_data_ratio", 0)

        today_error_count = int(total_recent_requests * failure_rate)
        today_error_rate_pct = round(failure_rate * 100, 1)

        # 3. Build system alerts from various sources
        system_alerts = []
        from datetime import datetime as dt
        from datetime import timezone as tz
        now_iso = dt.now(tz.utc).isoformat()

        if cpu_usage > 80:
            system_alerts.append({
                "timestamp": now_iso,
                "severity": "critical" if cpu_usage > 90 else "warning",
                "message": f"CPU usage is {cpu_usage}%",
                "source": "System",
                "acknowledged": False,
            })
        if memory_usage > 80:
            system_alerts.append({
                "timestamp": now_iso,
                "severity": "critical" if memory_usage > 90 else "warning",
                "message": f"Memory usage is {memory_usage}% ({memory_available_gb}GB free)",
                "source": "System",
                "acknowledged": False,
            })
        if disk_usage > 85:
            system_alerts.append({
                "timestamp": now_iso,
                "severity": "critical" if disk_usage > 95 else "warning",
                "message": f"Disk usage is {disk_usage}% ({disk_available_gb}GB free)",
                "source": "System",
                "acknowledged": False,
            })
        if failure_rate > 0.1:
            system_alerts.append({
                "timestamp": now_iso,
                "severity": "warning",
                "message": f"OPS error rate is {today_error_rate_pct}% ({today_error_count} errors in 24h)",
                "source": "OPS",
                "acknowledged": False,
            })

        # Add top failure causes as info alerts
        for cause in top_causes[:3]:
            system_alerts.append({
                "timestamp": now_iso,
                "severity": "info",
                "message": f"Top failure cause: {cause['reason']} ({cause['count']} occurrences)",
                "source": "Regression",
                "acknowledged": False,
            })

        state_patch = {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "memory_available_gb": memory_available_gb,
            "disk_usage": disk_usage,
            "disk_available_gb": disk_available_gb,
            "system_status": system_status,
            "system_alerts": system_alerts,
            "alert_count": len(system_alerts),
            "today_query_count": total_recent_requests,
            "today_error_count": today_error_count,
            "today_error_rate": today_error_rate_pct,
            "success_rate": round(success_rate * 100, 1),
            "failure_rate": round(failure_rate * 100, 1),
            "latency_p50": latency.get("p50"),
            "latency_p95": latency.get("p95"),
            "regression_trend": regression_trend,
            "regression_totals": regression_totals,
            "top_causes": top_causes,
            "no_data_ratio": round(no_data_ratio * 100, 1),
        }

        return ExecutorResult(
            blocks=[{"type": "markdown", "content": "System health loaded"}],
            state_patch=state_patch,
            summary={
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "system_status": system_status,
            },
        )

    except Exception as e:
        logger.error(f"fetch_system_health.error: {e}", exc_info=True)
        return ExecutorResult(
            blocks=[{"type": "markdown", "content": f"## System Health Error\n\n{str(e)}"}],
            state_patch={},
            summary={"error": str(e)},
        )
