"""
Action Handler Registry: Maps action_id to deterministic executors

Action handlers route UI actions to existing OPS executors (config, history, metric, graph, etc.)
without creating new API endpoints.

All handlers follow this signature:
    async def handler(inputs, context, session) -> ExecutorResult
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict
from sqlalchemy.orm import Session

from core.logging import get_logger

logger = get_logger(__name__)


class ExecutorResult:
    """Result from action executor"""

    def __init__(
        self,
        blocks: list[Dict[str, Any]],
        tool_calls: list[Dict[str, Any]] | None = None,
        references: list[Dict[str, Any]] | None = None,
        summary: Dict[str, Any] | None = None,
    ):
        self.blocks = blocks
        self.tool_calls = tool_calls or []
        self.references = references or []
        self.summary = summary or {}


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

        self._logger.info(f"Executing action: {action_id}", extra={"action_id": action_id})

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
    from ..services import handle_ops_query

    device_id = inputs.get("device_id")
    if not device_id:
        raise ValueError("device_id required")

    # Use existing config executor
    mode = "config"
    question = f"Show device detail for {device_id}"

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
    List maintenance tickets with filters (history executor)

    Inputs:
        - device_id: str (optional, empty = all)
        - offset: int
        - limit: int

    Returns:
        AnswerBlock with table of maintenance tickets
    """
    device_id = inputs.get("device_id", "")
    offset = inputs.get("offset", 0)
    limit = inputs.get("limit", 20)

    # TODO: Use history executor
    # Placeholder
    blocks = [
        {
            "type": "table",
            "columns": ["ID", "Device", "Type", "Status"],
            "rows": [
                ["M001", device_id or "All", "Preventive", "Scheduled"],
                ["M002", device_id or "All", "Corrective", "In Progress"],
            ],
        }
    ]

    return ExecutorResult(
        blocks=blocks,
        summary={"device_id": device_id, "offset": offset, "limit": limit, "total": 2},
    )


@register_action("create_maintenance_ticket")
async def handle_create_maintenance_ticket(
    inputs: Dict[str, Any], context: Dict[str, Any], session: Session
) -> ExecutorResult:
    """
    Create maintenance ticket (api_manager executor)

    Inputs:
        - op: "create"
        - device_id: str
        - maintenance_type: str
        - scheduled_date: str
        - assigned_to: str

    Returns:
        AnswerBlock confirming creation
    """
    device_id = inputs.get("device_id")
    maint_type = inputs.get("maintenance_type")
    scheduled_date = inputs.get("scheduled_date")

    if not all([device_id, maint_type, scheduled_date]):
        raise ValueError("Missing required fields")

    # TODO: Use api_manager executor for POST
    # Placeholder
    ticket_id = "MAINT-NEW-001"

    blocks = [
        {
            "type": "markdown",
            "content": f"Maintenance ticket #{ticket_id} created successfully",
        },
        {
            "type": "ui_screen",
            "screen_id": "maintenance_crud_v1",
            "params": {"list_mode": True},
        },
    ]

    return ExecutorResult(
        blocks=blocks,
        summary={"ticket_id": ticket_id, "device_id": device_id},
    )


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
    return ExecutorResult(blocks=blocks, summary={"state_patch": {"modal_open": True}})


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
    return ExecutorResult(blocks=blocks, summary={"state_patch": {"modal_open": False}})
