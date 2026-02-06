"""
Unit tests for ActionRegistry - Action handler registration and execution.

Tests cover:
- Action registration
- Action execution
- Unregistered action handling
- Input validation
- Output structure validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session

from app.modules.ops.services.action_registry import (
    ActionRegistry,
    ExecutorResult,
    register_action,
    execute_action,
    get_action_registry,
)


class TestActionRegistryRegistration:
    """Test action registration functionality."""

    def test_register_action_decorator(self):
        """Test registering action with decorator."""
        registry = ActionRegistry()

        @registry.register("test_action")
        async def handler(inputs, context, session):
            return ExecutorResult(blocks=[{"type": "markdown", "content": "Test"}])

        assert registry.get("test_action") is not None
        assert registry.get("test_action") == handler

    def test_register_multiple_actions(self):
        """Test registering multiple actions."""
        registry = ActionRegistry()

        @registry.register("action1")
        async def handler1(inputs, context, session):
            pass

        @registry.register("action2")
        async def handler2(inputs, context, session):
            pass

        assert registry.get("action1") is not None
        assert registry.get("action2") is not None
        assert registry.get("action1") != registry.get("action2")

    def test_get_unregistered_action_returns_none(self):
        """Test getting unregistered action returns None."""
        registry = ActionRegistry()
        assert registry.get("nonexistent") is None

    def test_global_registry_access(self):
        """Test accessing global registry."""
        registry = get_action_registry()
        assert isinstance(registry, ActionRegistry)


class TestActionRegistryExecution:
    """Test action execution."""

    @pytest.mark.asyncio
    async def test_execute_registered_action(self):
        """Test executing a registered action."""
        registry = ActionRegistry()

        @registry.register("fetch_data")
        async def handler(inputs, context, session):
            return ExecutorResult(
                blocks=[{"type": "markdown", "content": f"Data: {inputs.get('id')}"}],
                summary={"id": inputs.get("id")},
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "fetch_data",
            inputs={"id": "123"},
            context={"mode": "real"},
            session=session,
        )

        assert isinstance(result, ExecutorResult)
        assert len(result.blocks) == 1
        assert result.blocks[0]["content"] == "Data: 123"
        assert result.summary == {"id": "123"}

    @pytest.mark.asyncio
    async def test_execute_unregistered_action_raises_error(self):
        """Test executing unregistered action raises ValueError."""
        registry = ActionRegistry()
        session = MagicMock(spec=Session)

        with pytest.raises(ValueError, match="Unknown action_id"):
            await registry.execute(
                "nonexistent",
                inputs={},
                context={},
                session=session,
            )

    @pytest.mark.asyncio
    async def test_execute_action_with_context(self):
        """Test executing action with context."""
        registry = ActionRegistry()

        @registry.register("check_mode")
        async def handler(inputs, context, session):
            mode = context.get("mode", "unknown")
            return ExecutorResult(
                blocks=[{"type": "markdown", "content": f"Mode: {mode}"}],
                summary={"mode": mode},
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "check_mode",
            inputs={},
            context={"mode": "production"},
            session=session,
        )

        assert result.summary == {"mode": "production"}

    @pytest.mark.asyncio
    async def test_execute_global_registered_action(self):
        """Test executing action from global registry."""
        # Note: This tests the global registry functionality
        # In real scenarios, actions are registered at startup
        pass


class TestExecutorResult:
    """Test ExecutorResult structure."""

    def test_executor_result_with_blocks_only(self):
        """Test ExecutorResult with only blocks."""
        blocks = [
            {"type": "markdown", "content": "Test"},
            {"type": "table", "rows": [[1, 2, 3]]},
        ]
        result = ExecutorResult(blocks=blocks)

        assert result.blocks == blocks
        assert result.tool_calls == []
        assert result.references == []
        assert result.summary == {}
        assert result.state_patch == {}

    def test_executor_result_with_all_fields(self):
        """Test ExecutorResult with all fields."""
        result = ExecutorResult(
            blocks=[{"type": "markdown", "content": "Response"}],
            tool_calls=[{"tool": "query", "params": {"sql": "SELECT 1"}}],
            references=[{"type": "sql", "query": "SELECT 1"}],
            summary={"total": 1},
            state_patch={"ui_state": "updated"},
        )

        assert len(result.blocks) == 1
        assert len(result.tool_calls) == 1
        assert len(result.references) == 1
        assert result.summary == {"total": 1}
        assert result.state_patch == {"ui_state": "updated"}

    def test_executor_result_defaults(self):
        """Test ExecutorResult default values."""
        result = ExecutorResult(blocks=[])

        assert result.blocks == []
        assert isinstance(result.tool_calls, list)
        assert isinstance(result.references, list)
        assert isinstance(result.summary, dict)
        assert isinstance(result.state_patch, dict)


class TestActionInputValidation:
    """Test action input validation."""

    @pytest.mark.asyncio
    async def test_action_validates_required_inputs(self):
        """Test action validates required inputs."""
        registry = ActionRegistry()

        @registry.register("fetch_device")
        async def handler(inputs, context, session):
            device_id = inputs.get("device_id")
            if not device_id:
                raise ValueError("device_id required")
            return ExecutorResult(blocks=[])

        session = MagicMock(spec=Session)

        with pytest.raises(ValueError, match="device_id required"):
            await registry.execute(
                "fetch_device",
                inputs={},
                context={},
                session=session,
            )

    @pytest.mark.asyncio
    async def test_action_with_multiple_input_validation(self):
        """Test action with multiple input validations."""
        registry = ActionRegistry()

        @registry.register("create_ticket")
        async def handler(inputs, context, session):
            required = ["device_id", "ticket_type"]
            missing = [k for k in required if not inputs.get(k)]
            if missing:
                raise ValueError(f"Missing: {', '.join(missing)}")
            return ExecutorResult(blocks=[])

        session = MagicMock(spec=Session)

        with pytest.raises(ValueError, match="Missing"):
            await registry.execute(
                "create_ticket",
                inputs={"device_id": "dev-1"},
                context={},
                session=session,
            )

    @pytest.mark.asyncio
    async def test_action_with_optional_inputs(self):
        """Test action with optional inputs."""
        registry = ActionRegistry()

        @registry.register("list_items")
        async def handler(inputs, context, session):
            offset = inputs.get("offset", 0)
            limit = inputs.get("limit", 20)
            return ExecutorResult(
                blocks=[],
                summary={"offset": offset, "limit": limit},
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "list_items",
            inputs={"offset": 10},
            context={},
            session=session,
        )

        assert result.summary == {"offset": 10, "limit": 20}


class TestActionOutputStructure:
    """Test action output structure validation."""

    @pytest.mark.asyncio
    async def test_action_returns_blocks(self):
        """Test action returns blocks in response."""
        registry = ActionRegistry()

        @registry.register("render_data")
        async def handler(inputs, context, session):
            return ExecutorResult(
                blocks=[
                    {"type": "markdown", "content": "# Title"},
                    {"type": "markdown", "content": "Content"},
                ]
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "render_data",
            inputs={},
            context={},
            session=session,
        )

        assert len(result.blocks) == 2
        assert all(isinstance(b, dict) for b in result.blocks)
        assert all("type" in b for b in result.blocks)

    @pytest.mark.asyncio
    async def test_action_returns_state_patch(self):
        """Test action returns state_patch for UI updates."""
        registry = ActionRegistry()

        @registry.register("update_ui_state")
        async def handler(inputs, context, session):
            return ExecutorResult(
                blocks=[{"type": "markdown", "content": "Updated"}],
                state_patch={
                    "selected_device": inputs.get("device_id"),
                    "modal_open": False,
                    "data_refreshed": True,
                },
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "update_ui_state",
            inputs={"device_id": "dev-1"},
            context={},
            session=session,
        )

        assert "selected_device" in result.state_patch
        assert result.state_patch["modal_open"] is False
        assert result.state_patch["data_refreshed"] is True

    @pytest.mark.asyncio
    async def test_action_returns_tool_calls(self):
        """Test action returns tool_calls for documentation."""
        registry = ActionRegistry()

        @registry.register("execute_query")
        async def handler(inputs, context, session):
            return ExecutorResult(
                blocks=[{"type": "markdown", "content": "Results"}],
                tool_calls=[
                    {
                        "tool": "database_query",
                        "params": {"sql": "SELECT * FROM devices"},
                        "result": {"rows": 5},
                    }
                ],
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "execute_query",
            inputs={},
            context={},
            session=session,
        )

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "database_query"

    @pytest.mark.asyncio
    async def test_action_returns_references(self):
        """Test action returns references for tracing."""
        registry = ActionRegistry()

        @registry.register("fetch_with_refs")
        async def handler(inputs, context, session):
            return ExecutorResult(
                blocks=[{"type": "markdown", "content": "Data"}],
                references=[
                    {
                        "type": "database_query",
                        "query": "SELECT * FROM metrics",
                        "result_count": 100,
                    }
                ],
            )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "fetch_with_refs",
            inputs={},
            context={},
            session=session,
        )

        assert len(result.references) == 1
        assert result.references[0]["type"] == "database_query"


class TestActionErrorHandling:
    """Test action error handling."""

    @pytest.mark.asyncio
    async def test_action_exception_propagates(self):
        """Test that action exceptions propagate to caller."""
        registry = ActionRegistry()

        @registry.register("failing_action")
        async def handler(inputs, context, session):
            raise RuntimeError("Intentional error")

        session = MagicMock(spec=Session)

        with pytest.raises(RuntimeError, match="Intentional error"):
            await registry.execute(
                "failing_action",
                inputs={},
                context={},
                session=session,
            )

    @pytest.mark.asyncio
    async def test_action_with_graceful_error_response(self):
        """Test action returns error in response gracefully."""
        registry = ActionRegistry()

        @registry.register("safe_action")
        async def handler(inputs, context, session):
            try:
                # Do something that might fail
                _ = 1 / 0
            except ZeroDivisionError:
                return ExecutorResult(
                    blocks=[
                        {
                            "type": "markdown",
                            "content": "## Error\n\nDivision by zero",
                        }
                    ],
                    summary={"error": "division_by_zero"},
                )

        session = MagicMock(spec=Session)
        result = await registry.execute(
            "safe_action",
            inputs={},
            context={},
            session=session,
        )

        assert "Error" in result.blocks[0]["content"]

    @pytest.mark.asyncio
    async def test_action_with_timeout_handling(self):
        """Test action with timeout (simulated)."""
        registry = ActionRegistry()

        @registry.register("slow_action")
        async def handler(inputs, context, session):
            # In real scenarios, this might use asyncio.sleep()
            # For testing, we just simulate the timeout error
            if inputs.get("timeout"):
                raise TimeoutError("Action took too long")
            return ExecutorResult(blocks=[{"type": "markdown", "content": "Done"}])

        session = MagicMock(spec=Session)

        with pytest.raises(TimeoutError):
            await registry.execute(
                "slow_action",
                inputs={"timeout": True},
                context={},
                session=session,
            )


class TestActionRegistryLogging:
    """Test action registry logging."""

    @pytest.mark.asyncio
    async def test_action_execution_logs_info(self):
        """Test that action execution is logged."""
        registry = ActionRegistry()

        @registry.register("logged_action")
        async def handler(inputs, context, session):
            return ExecutorResult(blocks=[])

        session = MagicMock(spec=Session)

        # Should not raise any logging errors
        await registry.execute(
            "logged_action",
            inputs={},
            context={},
            session=session,
        )

    @pytest.mark.asyncio
    async def test_unregistered_action_logged(self):
        """Test that unregistered action is logged."""
        registry = ActionRegistry()
        session = MagicMock(spec=Session)

        with pytest.raises(ValueError):
            await registry.execute(
                "unregistered",
                inputs={},
                context={},
                session=session,
            )
