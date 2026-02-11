"""
Test suite for OPS module route structure and imports

Validates that all modularized routes are properly organized and importable.
Tests basic endpoint availability without requiring a full database setup.
"""

import pytest


def test_ops_routes_import():
    """Test that all route modules can be imported."""
    from app.modules.ops import routes

    # Verify all route modules are available
    assert hasattr(routes, "query_router")
    assert hasattr(routes, "ask_router")
    assert hasattr(routes, "ui_actions_router")
    assert hasattr(routes, "rca_router")
    assert hasattr(routes, "regression_router")
    assert hasattr(routes, "actions_router")
    assert hasattr(routes, "threads_router")


def test_combined_router_creation():
    """Test that combined router can be created."""
    from app.modules.ops.routes import get_combined_router

    router = get_combined_router()
    assert router is not None
    assert router.prefix == "/ops"
    assert "ops" in router.tags


def test_error_classes_import():
    """Test that error classes can be imported."""
    from app.modules.ops.errors import (
        ExecutionException,
        OPSException,
        PlanningException,
        StageExecutionException,
        ToolNotFoundException,
        ValidationException,
    )

    # Verify all error classes exist
    assert OPSException is not None
    assert PlanningException is not None
    assert ExecutionException is not None
    assert ValidationException is not None
    assert ToolNotFoundException is not None
    assert StageExecutionException is not None


def test_error_class_hierarchy():
    """Test that error classes have correct inheritance."""
    from app.modules.ops.errors import (
        ExecutionException,
        OPSException,
        PlanningException,
        StageExecutionException,
        ToolNotFoundException,
        ValidationException,
    )

    # All should inherit from OPSException
    assert issubclass(PlanningException, OPSException)
    assert issubclass(ExecutionException, OPSException)
    assert issubclass(ValidationException, OPSException)
    assert issubclass(ToolNotFoundException, OPSException)
    assert issubclass(StageExecutionException, OPSException)


def test_error_to_dict_method():
    """Test error to_dict() method."""
    from app.modules.ops.errors import ValidationException

    error = ValidationException(
        "Invalid input",
        code=400,
        details={"field": "question"}
    )

    error_dict = error.to_dict()
    assert error_dict["code"] == 400
    assert error_dict["message"] == "Invalid input"
    assert error_dict["details"] == {"field": "question"}


def test_error_handler_import():
    """Test that error handlers can be imported."""
    from app.modules.ops.error_handler import (
        execution_exception_handler,
        ops_exception_handler,
        planning_exception_handler,
        register_exception_handlers,
        stage_execution_exception_handler,
        tool_not_found_handler,
        validation_exception_handler,
    )

    assert register_exception_handlers is not None
    assert ops_exception_handler is not None
    assert planning_exception_handler is not None
    assert execution_exception_handler is not None
    assert validation_exception_handler is not None
    assert tool_not_found_handler is not None
    assert stage_execution_exception_handler is not None


def test_route_utils_import():
    """Test that route utilities can be imported."""
    from app.modules.ops.routes.utils import (
        _tenant_id,
        apply_patch,
        generate_references_from_tool_calls,
    )

    assert _tenant_id is not None
    assert generate_references_from_tool_calls is not None
    assert apply_patch is not None


def test_generate_references_from_tool_calls():
    """Test generate_references_from_tool_calls utility function."""
    from app.modules.ops.routes.utils import generate_references_from_tool_calls

    # Test with empty list
    result = generate_references_from_tool_calls([])
    assert result == []

    # Test with valid tool call
    tool_calls = [
        {
            "tool": "test_tool",
            "params": {"key": "value"},
            "result": "test_result"
        }
    ]
    result = generate_references_from_tool_calls(tool_calls)
    assert len(result) == 1
    assert result[0]["tool_name"] == "test_tool"
    assert result[0]["type"] == "tool_call"
    assert result[0]["index"] == 0
    assert "result_summary" in result[0]


def test_route_files_exist():
    """Test that all expected route files exist."""
    from pathlib import Path

    ops_routes_dir = Path(__file__).parent.parent / "app" / "modules" / "ops" / "routes"

    expected_files = [
        "__init__.py",
        "utils.py",
        "query.py",
        "ci_ask.py",
        "ui_actions.py",
        "rca.py",
        "regression.py",
        "actions.py",
        "threads.py",
    ]

    for expected_file in expected_files:
        file_path = ops_routes_dir / expected_file
        assert file_path.exists(), f"Expected file {expected_file} not found"


def test_error_files_exist():
    """Test that error handling files exist."""
    from pathlib import Path

    ops_dir = Path(__file__).parent.parent / "app" / "modules" / "ops"

    assert (ops_dir / "errors.py").exists()
    assert (ops_dir / "error_handler.py").exists()
    assert (ops_dir / "REFACTORING_SUMMARY.md").exists()


def test_backward_compatibility():
    """Test that original router import still works."""
    # Old import style should still work
    try:
        from app.modules.ops import router
        assert router is not None
    except ImportError:
        pytest.fail("Backward compatibility broken - cannot import router from ops")


class TestRouterStructure:
    """Test suite for router structure validation."""

    def test_query_router_has_endpoints(self):
        """Test that query router has required endpoints."""
        from app.modules.ops.routes.query import router

        # Check that router has routes defined
        assert len(router.routes) > 0

    def test_rca_router_has_endpoints(self):
        """Test that RCA router has required endpoints."""
        from app.modules.ops.routes.rca import router

        # Check that router has routes defined
        assert len(router.routes) > 0

    def test_regression_router_has_endpoints(self):
        """Test that regression router has required endpoints."""
        from app.modules.ops.routes.regression import router

        # Check that router has routes defined
        assert len(router.routes) > 0

    def test_actions_router_has_endpoints(self):
        """Test that actions router has required endpoints."""
        from app.modules.ops.routes.actions import router

        # Check that router has routes defined
        assert len(router.routes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
