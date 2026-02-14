"""
Tool Capability Registry (P1-2)
Declares capabilities and constraints for each tool in the orchestration system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CapabilityType(str, Enum):
    """Types of tool capabilities (P1-2)"""
    READ_WRITE = "read_write"        # Can read and write
    READ_ONLY = "read_only"          # Read-only access
    APPEND_ONLY = "append_only"      # Can only append new data
    TIME_SERIES = "time_series"      # Time-series data access
    API_CALL = "api_call"            # External API call
    GRAPH_QUERY = "graph_query"      # Graph database query
    SEARCH = "search"                # Full-text or vector search


class ExecutionMode(str, Enum):
    """Execution modes for tools (P1-2)"""
    SERIAL = "serial"                # Execute one at a time
    PARALLEL = "parallel"            # Can execute in parallel
    STREAMING = "streaming"          # Streaming results
    BATCH = "batch"                  # Batch processing


@dataclass
class ToolCapability:
    """
    Capability declaration for each tool (P1-2)
    Used by orchestrator to make execution decisions
    """
    # Identification
    tool_id: str
    tool_name: str
    tool_type: str  # "sql" | "http" | "llm" | "graph" | "search"

    # Capability classification
    capability_type: CapabilityType
    execution_mode: ExecutionMode

    # Performance constraints
    max_concurrent_calls: int = 10
    timeout_seconds: int = 30
    rate_limit_per_minute: int = 100
    max_result_size_mb: int = 50

    # Data access constraints
    supported_tenants: Optional[list[str]] = None  # None = all tenants
    max_rows: int = 10000
    requires_authentication: bool = True

    # Reliability
    fallback_enabled: bool = True
    fallback_tool_id: Optional[str] = None
    retry_count: int = 3
    retry_delay_seconds: int = 1

    # Dependencies
    depends_on: list[str] = field(default_factory=list)  # Other tool_ids this tool depends on

    # Metadata
    version: str = "1.0"
    deprecated: bool = False
    description: str = ""


class ToolCapabilityRegistry:
    """Registry for all tool capabilities (P1-2)"""

    def __init__(self):
        self._registry: dict[str, ToolCapability] = {}

    def register(self, capability: ToolCapability) -> None:
        """Register a tool capability"""
        self._registry[capability.tool_id] = capability

    def get(self, tool_id: str) -> Optional[ToolCapability]:
        """Get capability for a tool"""
        return self._registry.get(tool_id)

    def get_all(self) -> dict[str, ToolCapability]:
        """Get all registered capabilities"""
        return self._registry.copy()

    def get_by_type(self, capability_type: CapabilityType) -> list[ToolCapability]:
        """Get all tools with a specific capability type"""
        return [cap for cap in self._registry.values() if cap.capability_type == capability_type]

    def get_parallelizable(self) -> list[ToolCapability]:
        """Get all tools that can execute in parallel"""
        return [cap for cap in self._registry.values() if cap.execution_mode == ExecutionMode.PARALLEL]

    def can_execute_in_parallel(self, tool_ids: list[str]) -> bool:
        """Check if all tools can execute in parallel"""
        for tool_id in tool_ids:
            cap = self.get(tool_id)
            if not cap or cap.execution_mode != ExecutionMode.PARALLEL:
                return False
        return True

    def check_dependencies(self, tool_id: str) -> list[str]:
        """Get dependency tree for a tool"""
        cap = self.get(tool_id)
        if not cap:
            return []
        return cap.depends_on

    def validate_tenant_access(self, tool_id: str, tenant_id: str) -> bool:
        """Validate if a tool supports a specific tenant"""
        cap = self.get(tool_id)
        if not cap:
            return False
        # None means all tenants supported
        if cap.supported_tenants is None:
            return True
        return tenant_id in cap.supported_tenants

    def can_fallback(self, tool_id: str) -> bool:
        """Check if a tool has fallback enabled"""
        cap = self.get(tool_id)
        if not cap:
            return False
        return cap.fallback_enabled and cap.fallback_tool_id is not None


# Global registry instance
_global_registry = ToolCapabilityRegistry()


def get_capability_registry() -> ToolCapabilityRegistry:
    """Get the global capability registry"""
    return _global_registry


def register_capability(capability: ToolCapability) -> None:
    """Register a tool capability in the global registry"""
    _global_registry.register(capability)


# Built-in tool capabilities (P1-2)
def initialize_default_capabilities() -> None:
    """Initialize default tool capabilities"""

    # Direct Query Tool (SQL)
    register_capability(
        ToolCapability(
            tool_id="direct_query",
            tool_name="Direct Query Tool",
            tool_type="sql",
            capability_type=CapabilityType.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            max_concurrent_calls=20,
            timeout_seconds=30,
            rate_limit_per_minute=120,
            max_result_size_mb=50,
            max_rows=10000,
            requires_authentication=True,
            fallback_enabled=True,
            retry_count=3,
            description="Execute read-only SQL queries on the database",
        )
    )

    # HTTP Tool
    register_capability(
        ToolCapability(
            tool_id="http_tool",
            tool_name="HTTP API Tool",
            tool_type="http",
            capability_type=CapabilityType.API_CALL,
            execution_mode=ExecutionMode.PARALLEL,
            max_concurrent_calls=10,
            timeout_seconds=60,
            rate_limit_per_minute=60,
            max_result_size_mb=10,
            requires_authentication=True,
            fallback_enabled=True,
            retry_count=2,
            description="Call external HTTP APIs",
        )
    )

    # Graph Query Tool
    register_capability(
        ToolCapability(
            tool_id="graph_query",
            tool_name="Graph Query Tool",
            tool_type="graph",
            capability_type=CapabilityType.GRAPH_QUERY,
            execution_mode=ExecutionMode.PARALLEL,
            max_concurrent_calls=15,
            timeout_seconds=45,
            rate_limit_per_minute=100,
            max_result_size_mb=30,
            requires_authentication=True,
            fallback_enabled=True,
            retry_count=2,
            description="Query relationships in the graph database",
        )
    )

    # Document Search Tool
    register_capability(
        ToolCapability(
            tool_id="document_search",
            tool_name="Document Search Tool",
            tool_type="search",
            capability_type=CapabilityType.SEARCH,
            execution_mode=ExecutionMode.PARALLEL,
            max_concurrent_calls=5,
            timeout_seconds=30,
            rate_limit_per_minute=50,
            max_result_size_mb=20,
            max_rows=100,  # Limit results for search
            requires_authentication=False,
            fallback_enabled=False,
            description="Search documents using hybrid search (BM25 + vector)",
        )
    )

    # LLM Tool
    register_capability(
        ToolCapability(
            tool_id="llm_tool",
            tool_name="LLM Tool",
            tool_type="llm",
            capability_type=CapabilityType.READ_WRITE,
            execution_mode=ExecutionMode.SERIAL,  # LLM typically runs serially
            max_concurrent_calls=1,
            timeout_seconds=120,
            rate_limit_per_minute=30,
            max_result_size_mb=5,
            requires_authentication=True,
            fallback_enabled=False,
            retry_count=1,
            description="Call LLM for analysis and composition",
        )
    )

    # Baseline Metrics Tool
    register_capability(
        ToolCapability(
            tool_id="baseline_metrics",
            tool_name="Baseline Metrics Tool",
            tool_type="sql",
            capability_type=CapabilityType.TIME_SERIES,
            execution_mode=ExecutionMode.PARALLEL,
            max_concurrent_calls=10,
            timeout_seconds=30,
            rate_limit_per_minute=100,
            max_result_size_mb=50,
            max_rows=1000,
            requires_authentication=True,
            fallback_enabled=True,
            description="Retrieve baseline metrics from time-series data",
        )
    )
