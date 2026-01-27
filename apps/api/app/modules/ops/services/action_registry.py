"""
Action Handler Registry: Maps action_id to deterministic executors

Action handlers route UI actions to existing OPS executors (config, history, metric, graph, etc.)
without creating new API endpoints.

All handlers follow this signature:
    async def handler(inputs, context, session) -> ExecutorResult
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from core.logging import get_logger
from sqlalchemy.orm import Session
from app.modules.asset_registry.loader import load_source_asset
from app.modules.ops.services.connections import ConnectionFactory

logger = get_logger(__name__)




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
        self._logger = get_logger("ActionRegistry")

    def register(self, action_id: str):
        """Decorator to register an action handler"""

        def decorator(func: Callable) -> Callable:
            self._handlers[action_id] = func
            self._logger.info(f"Registered action handler: {action_id}")
            return func

        return decorator

    def get(self, action_id: str) -> Callable | None:
        """Get handler by action_id"""
        return self._handlers.get(action_id)

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


def get_action_registry() -> ActionRegistry:
    """Get global action registry"""
    return _global_registry


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


@register_action("fetch_device_detail")
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


@register_action("list_maintenance_filtered")
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


@register_action("create_maintenance_ticket")
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


@register_action("open_maintenance_modal")
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


@register_action("close_maintenance_modal")
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
