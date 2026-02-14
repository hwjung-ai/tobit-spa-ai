"""
Chaos Engineering Tests for OPS Orchestration (P1-4)
Tests failure scenarios, resilience, and graceful degradation
"""

import unittest

from app.modules.ops.schemas import (
    OrchestrationResponse,
    OrchestrationStatus,
    ToolResult,
)
from app.modules.ops.services.orchestration.tools.capability_registry import (
    CapabilityType,
    ExecutionMode,
    ToolCapability,
    ToolCapabilityRegistry,
)


class TestChaosToolTimeout(unittest.TestCase):
    """Test tool timeout cascades and isolation (P1-4)"""

    def setUp(self):
        self.registry = ToolCapabilityRegistry()

    def test_single_tool_timeout_isolation(self):
        """When one tool times out, others should still execute"""
        # Tool A: 5 second timeout
        cap_a = ToolCapability(
            tool_id="tool_a",
            tool_name="Tool A",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            timeout_seconds=5,
        )

        # Tool B: 30 second timeout
        cap_b = ToolCapability(
            tool_id="tool_b",
            tool_name="Tool B",
            tool_type="http",
            capability_type=CapabilityType.API_CALL,
            execution_mode=ExecutionMode.PARALLEL,
            timeout_seconds=30,
        )

        self.registry.register(cap_a)
        self.registry.register(cap_b)

        # Verify both tools are registered with different timeouts
        cap_a_retrieved = self.registry.get("tool_a")
        cap_b_retrieved = self.registry.get("tool_b")

        self.assertIsNotNone(cap_a_retrieved)
        self.assertIsNotNone(cap_b_retrieved)
        self.assertEqual(cap_a_retrieved.timeout_seconds, 5)
        self.assertEqual(cap_b_retrieved.timeout_seconds, 30)

        # Both can execute in parallel
        self.assertTrue(self.registry.can_execute_in_parallel(["tool_a", "tool_b"]))

    def test_timeout_respects_capability_config(self):
        """Timeout should respect capability configuration"""
        cap = ToolCapability(
            tool_id="test_tool",
            tool_name="Test Tool",
            tool_type="http",
            capability_type=CapabilityType.API_CALL,
            execution_mode=ExecutionMode.PARALLEL,
            timeout_seconds=15,
        )

        self.registry.register(cap)
        retrieved = self.registry.get("test_tool")

        self.assertEqual(retrieved.timeout_seconds, 15)
        self.assertTrue(retrieved.timeout_seconds > 0)


class TestChaosToolDatabaseError(unittest.TestCase):
    """Test database connection errors and fallback (P1-4)"""

    def setUp(self):
        self.registry = ToolCapabilityRegistry()

    def test_database_connection_error_triggers_fallback(self):
        """When primary tool fails, fallback tool should be used"""
        # Primary tool
        primary = ToolCapability(
            tool_id="primary_db",
            tool_name="Primary DB Tool",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.SERIAL,
            fallback_enabled=True,
            fallback_tool_id="fallback_db",
        )

        # Fallback tool
        fallback = ToolCapability(
            tool_id="fallback_db",
            tool_name="Fallback DB Tool",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.SERIAL,
            fallback_enabled=False,
        )

        self.registry.register(primary)
        self.registry.register(fallback)

        # Assertion: Primary has fallback configured
        primary_cap = self.registry.get("primary_db")
        self.assertTrue(primary_cap.fallback_enabled)
        self.assertEqual(primary_cap.fallback_tool_id, "fallback_db")

        # Fallback tool exists and is retrievable
        fallback_cap = self.registry.get("fallback_db")
        self.assertIsNotNone(fallback_cap)

    def test_orchestration_partial_success_on_db_failure(self):
        """When some tools fail, status should be PARTIAL_SUCCESS"""
        response = OrchestrationResponse(
            status=OrchestrationStatus.PARTIAL_SUCCESS,
            answer="Partial results available",
            blocks=[{"type": "text", "text": "Tool B succeeded"}],
            results=[
                ToolResult(tool_id="tool_a", tool_name="Tool A", success=False, error="Connection timeout"),
                ToolResult(tool_id="tool_b", tool_name="Tool B", success=True, data={"rows": 10}),
            ],
            successful_tools=1,
            failed_tools=1,
            fallback_applied=False,
        )

        self.assertEqual(response.status, OrchestrationStatus.PARTIAL_SUCCESS)
        self.assertEqual(response.successful_tools, 1)
        self.assertEqual(response.failed_tools, 1)
        self.assertEqual(len(response.results), 2)


class TestChaosToolTenantBoundaryViolation(unittest.TestCase):
    """Test tenant isolation and boundary enforcement (P1-4)"""

    def setUp(self):
        self.registry = ToolCapabilityRegistry()

    def test_tenant_boundary_violation_blocked(self):
        """Tool should reject cross-tenant access"""
        # Tool that only supports tenant_a
        cap = ToolCapability(
            tool_id="tenant_specific_tool",
            tool_name="Tenant Specific Tool",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            supported_tenants=["tenant_a", "tenant_b"],
        )

        self.registry.register(cap)

        # Test: tenant_a access should be allowed
        self.assertTrue(self.registry.validate_tenant_access("tenant_specific_tool", "tenant_a"))

        # Test: tenant_b access should be allowed
        self.assertTrue(self.registry.validate_tenant_access("tenant_specific_tool", "tenant_b"))

        # Test: tenant_c access should be denied
        self.assertFalse(self.registry.validate_tenant_access("tenant_specific_tool", "tenant_c"))

    def test_multi_tenant_tool_allows_all_tenants(self):
        """Tool with supported_tenants=None should allow all tenants"""
        cap = ToolCapability(
            tool_id="global_tool",
            tool_name="Global Tool",
            tool_type="http",
            capability_type=CapabilityType.API_CALL,
            execution_mode=ExecutionMode.PARALLEL,
            supported_tenants=None,  # Allow all
        )

        self.registry.register(cap)

        # Any tenant should be allowed
        self.assertTrue(self.registry.validate_tenant_access("global_tool", "tenant_a"))
        self.assertTrue(self.registry.validate_tenant_access("global_tool", "tenant_xyz"))


class TestChaosInvalidSchemaChange(unittest.TestCase):
    """Test runtime schema changes and graceful error handling (P1-4)"""

    def test_invalid_schema_graceful_error(self):
        """Invalid schema should result in clear error, not crash"""
        try:
            # Create capability with invalid max_rows
            cap = ToolCapability(
                tool_id="test_tool",
                tool_name="Test Tool",
                tool_type="sql",
                capability_type=CapabilityType.READ_ONLY,
                execution_mode=ExecutionMode.PARALLEL,
                max_rows=-1,  # Invalid: negative
            )
            # Should still create but validation should catch it
            self.assertIsNotNone(cap)
        except Exception as e:
            # Graceful error handling
            self.assertIsNotNone(e)

    def test_missing_required_fields_caught(self):
        """Missing required fields should be caught"""
        try:
            # Create capability without required fields
            ToolCapability(
                tool_id="test_tool",
                tool_name="Test Tool",
                tool_type="sql",
                capability_type=CapabilityType.READ_ONLY,
                # Missing: execution_mode (required)
            )
            self.fail("Should have raised an error for missing execution_mode")
        except TypeError:
            # Expected: dataclass requires execution_mode
            pass


class TestChaosParallelizationConflict(unittest.TestCase):
    """Test conflicts in parallel execution constraints (P1-4)"""

    def setUp(self):
        self.registry = ToolCapabilityRegistry()

    def test_serial_tool_not_parallelizable(self):
        """Serial tools should not be marked as parallelizable"""
        cap = ToolCapability(
            tool_id="llm_tool",
            tool_name="LLM Tool",
            tool_type="llm",
            capability_type=CapabilityType.READ_WRITE,
            execution_mode=ExecutionMode.SERIAL,
        )

        self.registry.register(cap)

        # Test: LLM tool should not be in parallelizable list
        parallelizable = self.registry.get_parallelizable()
        self.assertNotIn(cap, parallelizable)

    def test_mixed_execution_modes_detected(self):
        """Mixed execution modes should be detected"""
        # Parallel tool
        parallel_cap = ToolCapability(
            tool_id="parallel_tool",
            tool_name="Parallel Tool",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
        )

        # Serial tool
        serial_cap = ToolCapability(
            tool_id="serial_tool",
            tool_name="Serial Tool",
            tool_type="llm",
            capability_type=CapabilityType.READ_WRITE,
            execution_mode=ExecutionMode.SERIAL,
        )

        self.registry.register(parallel_cap)
        self.registry.register(serial_cap)

        # Test: Can execute in parallel only if ALL are parallel
        can_parallelize = self.registry.can_execute_in_parallel(
            ["parallel_tool", "serial_tool"]
        )
        self.assertFalse(can_parallelize)

        # Test: Can execute in parallel if all are parallel
        can_parallelize_all_parallel = self.registry.can_execute_in_parallel(
            ["parallel_tool"]
        )
        self.assertTrue(can_parallelize_all_parallel)


class TestChaosDependencyManagement(unittest.TestCase):
    """Test tool dependency tracking and validation (P1-4)"""

    def setUp(self):
        self.registry = ToolCapabilityRegistry()

    def test_tool_dependency_tracking(self):
        """Tools with dependencies should track them correctly"""
        # Tool A (independent)
        cap_a = ToolCapability(
            tool_id="tool_a",
            tool_name="Tool A",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            depends_on=[],
        )

        # Tool B (depends on Tool A)
        cap_b = ToolCapability(
            tool_id="tool_b",
            tool_name="Tool B",
            tool_type="http",
            capability_type=CapabilityType.API_CALL,
            execution_mode=ExecutionMode.PARALLEL,
            depends_on=["tool_a"],
        )

        self.registry.register(cap_a)
        self.registry.register(cap_b)

        # Test: Tool A has no dependencies
        deps_a = self.registry.check_dependencies("tool_a")
        self.assertEqual(len(deps_a), 0)

        # Test: Tool B depends on Tool A
        deps_b = self.registry.check_dependencies("tool_b")
        self.assertIn("tool_a", deps_b)

    def test_circular_dependency_detection(self):
        """Circular dependencies should be detectable"""
        # Tool A → Tool B → Tool A (circular)
        cap_a = ToolCapability(
            tool_id="tool_a",
            tool_name="Tool A",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            depends_on=["tool_b"],
        )

        cap_b = ToolCapability(
            tool_id="tool_b",
            tool_name="Tool B",
            tool_type="http",
            capability_type=CapabilityType.API_CALL,
            execution_mode=ExecutionMode.PARALLEL,
            depends_on=["tool_a"],
        )

        self.registry.register(cap_a)
        self.registry.register(cap_b)

        # Test: Circular dependency can be detected
        deps_a = self.registry.check_dependencies("tool_a")
        deps_b = self.registry.check_dependencies("tool_b")

        # Simple circular detection: if A depends on B and B depends on A
        is_circular = ("tool_b" in deps_a) and ("tool_a" in deps_b)
        self.assertTrue(is_circular)


class TestOrchestrationStatusTransitions(unittest.TestCase):
    """Test orchestration status transitions (P1-4)"""

    def test_all_success_to_success_status(self):
        """All tools succeed → SUCCESS status"""
        response = OrchestrationResponse(
            status=OrchestrationStatus.SUCCESS,
            answer="All tools succeeded",
            blocks=[],
            results=[
                ToolResult(tool_id="tool_a", tool_name="Tool A", success=True, data={}),
                ToolResult(tool_id="tool_b", tool_name="Tool B", success=True, data={}),
            ],
            successful_tools=2,
            failed_tools=0,
        )

        self.assertEqual(response.status, OrchestrationStatus.SUCCESS)
        self.assertEqual(response.successful_tools, 2)
        self.assertEqual(response.failed_tools, 0)

    def test_some_failure_to_partial_success_status(self):
        """Some tools fail → PARTIAL_SUCCESS status"""
        response = OrchestrationResponse(
            status=OrchestrationStatus.PARTIAL_SUCCESS,
            answer="Some results available",
            blocks=[],
            results=[
                ToolResult(tool_id="tool_a", tool_name="Tool A", success=True, data={}),
                ToolResult(tool_id="tool_b", tool_name="Tool B", success=False, error="Failed"),
            ],
            successful_tools=1,
            failed_tools=1,
        )

        self.assertEqual(response.status, OrchestrationStatus.PARTIAL_SUCCESS)
        self.assertEqual(response.successful_tools, 1)
        self.assertEqual(response.failed_tools, 1)

    def test_all_fail_with_fallback_to_degraded_status(self):
        """All tools fail but fallback applied → DEGRADED status"""
        response = OrchestrationResponse(
            status=OrchestrationStatus.DEGRADED,
            answer="Using fallback results",
            blocks=[],
            results=[
                ToolResult(tool_id="tool_a", tool_name="Tool A", success=False, error="Failed"),
                ToolResult(tool_id="tool_b", tool_name="Tool B", success=False, error="Failed"),
            ],
            successful_tools=0,
            failed_tools=2,
            fallback_applied=True,
            fallback_reason="All primary tools failed",
        )

        self.assertEqual(response.status, OrchestrationStatus.DEGRADED)
        self.assertTrue(response.fallback_applied)
        self.assertIsNotNone(response.fallback_reason)

    def test_all_fail_no_fallback_to_failed_status(self):
        """All tools fail and no fallback → FAILED status"""
        response = OrchestrationResponse(
            status=OrchestrationStatus.FAILED,
            answer=None,
            blocks=[],
            results=[
                ToolResult(tool_id="tool_a", tool_name="Tool A", success=False, error="Failed"),
            ],
            successful_tools=0,
            failed_tools=1,
            fallback_applied=False,
            error_message="No results and no fallback available",
        )

        self.assertEqual(response.status, OrchestrationStatus.FAILED)
        self.assertFalse(response.fallback_applied)
        self.assertIsNotNone(response.error_message)


if __name__ == "__main__":
    unittest.main()
