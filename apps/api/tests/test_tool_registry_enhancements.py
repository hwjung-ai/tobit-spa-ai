"""Unit tests for Tool Registry enhancements (Phase 2)."""


from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolRegistry,
    ToolResult,
    get_tool_registry,
)
from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name: str = "mock_tool"):
        super().__init__()
        self._name = name
        self._input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            }
        }
        self._output_schema = {
            "type": "object",
            "properties": {
                "results": {"type": "array", "description": "Search results"}
            }
        }

    @property
    def tool_type(self) -> str:
        return "mock"

    @property
    def tool_name(self) -> str:
        return self._name

    @property
    def input_schema(self) -> dict:
        return self._input_schema

    @property
    def output_schema(self) -> dict:
        return self._output_schema

    async def should_execute(self, context: ToolContext, params: dict) -> bool:
        return True

    async def execute(self, context: ToolContext, params: dict) -> ToolResult:
        return ToolResult(success=True, data={"results": []})


class TestToolInputOutputSchema:
    """Test input_schema and output_schema properties."""

    def test_base_tool_has_schema_properties(self):
        """BaseTool should have input_schema and output_schema properties."""
        tool = MockTool()
        assert hasattr(tool, "input_schema")
        assert hasattr(tool, "output_schema")

    def test_base_tool_default_schemas_are_none(self):
        """BaseTool default schemas should be None."""
        # Create a minimal concrete tool
        class MinimalTool(BaseTool):
            @property
            def tool_type(self) -> str:
                return "minimal"

            async def should_execute(self, context, params):
                return True

            async def execute(self, context, params):
                return ToolResult(success=True)

        tool = MinimalTool()
        assert tool.input_schema is None
        assert tool.output_schema is None

    def test_mock_tool_has_schemas(self):
        """MockTool should return defined schemas."""
        tool = MockTool()
        assert tool.input_schema is not None
        assert tool.output_schema is not None
        assert "properties" in tool.input_schema
        assert "properties" in tool.output_schema

    def test_dynamic_tool_has_schemas(self):
        """DynamicTool should expose input and output schemas."""
        tool_asset = {
            "name": "test_query_tool",
            "tool_type": "database_query",
            "tool_config": {"query": "SELECT * FROM data"},
            "tool_input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}}
            },
            "tool_output_schema": {
                "type": "object",
                "properties": {"rows": {"type": "array"}}
            }
        }
        tool = DynamicTool(tool_asset)
        assert tool.input_schema == tool_asset["tool_input_schema"]
        assert tool.output_schema == tool_asset["tool_output_schema"]

    def test_dynamic_tool_default_schemas(self):
        """DynamicTool should have default empty schemas."""
        tool_asset = {
            "name": "minimal_tool",
            "tool_type": "custom"
        }
        tool = DynamicTool(tool_asset)
        assert tool.input_schema == {}
        assert tool.output_schema == {}


class TestToolRegistryInfoMethods:
    """Test new info retrieval methods in ToolRegistry."""

    def test_get_tool_info_single_tool(self):
        """get_tool_info should return tool information."""
        registry = ToolRegistry()
        tool = MockTool(name="test_tool")
        registry.register_dynamic(tool)

        info = registry.get_tool_info("test_tool")
        assert info is not None
        assert info["name"] == "test_tool"
        assert info["type"] == "mock"
        assert info["input_schema"] == tool.input_schema
        assert info["output_schema"] == tool.output_schema

    def test_get_tool_info_not_found(self):
        """get_tool_info should return None for unregistered tool."""
        registry = ToolRegistry()
        info = registry.get_tool_info("nonexistent")
        assert info is None

    def test_get_all_tools_info(self):
        """get_all_tools_info should return info for all tools."""
        registry = ToolRegistry()
        tool1 = MockTool(name="tool1")
        tool2 = MockTool(name="tool2")
        registry.register_dynamic(tool1)
        registry.register_dynamic(tool2)

        tools_info = registry.get_all_tools_info()
        assert len(tools_info) == 2
        tool_names = [info["name"] for info in tools_info]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_get_all_tools_info_empty_registry(self):
        """get_all_tools_info should return empty list for empty registry."""
        registry = ToolRegistry()
        tools_info = registry.get_all_tools_info()
        assert tools_info == []

    def test_validate_tool_type_exists(self):
        """validate_tool_type should return True for registered tool."""
        registry = ToolRegistry()
        tool = MockTool(name="valid_tool")
        registry.register_dynamic(tool)

        assert registry.validate_tool_type("valid_tool") is True

    def test_validate_tool_type_not_exists(self):
        """validate_tool_type should return False for unregistered tool."""
        registry = ToolRegistry()
        assert registry.validate_tool_type("invalid_tool") is False

    def test_get_all_tools_info_with_dynamic_tools(self):
        """get_all_tools_info should work with DynamicTools."""
        registry = ToolRegistry()

        # Register DynamicTool with schemas
        tool_asset1 = {
            "name": "query_tool",
            "tool_type": "database_query",
            "tool_input_schema": {"properties": {"sql": {"type": "string"}}},
            "tool_output_schema": {"properties": {"rows": {"type": "array"}}}
        }
        tool1 = DynamicTool(tool_asset1)
        registry.register_dynamic(tool1)

        # Register DynamicTool without schemas
        tool_asset2 = {
            "name": "simple_tool",
            "tool_type": "custom"
        }
        tool2 = DynamicTool(tool_asset2)
        registry.register_dynamic(tool2)

        tools_info = registry.get_all_tools_info()
        assert len(tools_info) == 2

        # Verify tool with schemas
        query_tool_info = next(info for info in tools_info if info["name"] == "query_tool")
        assert query_tool_info["input_schema"] != {}
        assert query_tool_info["output_schema"] != {}

        # Verify tool without schemas
        simple_tool_info = next(info for info in tools_info if info["name"] == "simple_tool")
        assert simple_tool_info["input_schema"] == {}
        assert simple_tool_info["output_schema"] == {}


class TestToolRegistrySchemaInfo:
    """Test that tool info includes complete schema information."""

    def test_tool_info_structure(self):
        """Tool info should have expected structure."""
        registry = ToolRegistry()
        tool = MockTool(name="structured_tool")
        registry.register_dynamic(tool)

        info = registry.get_tool_info("structured_tool")
        expected_keys = {"name", "type", "input_schema", "output_schema"}
        assert set(info.keys()) == expected_keys

    def test_tool_info_schema_preservation(self):
        """Tool info should preserve schema details."""
        registry = ToolRegistry()
        tool_asset = {
            "name": "detailed_tool",
            "tool_type": "database_query",
            "tool_input_schema": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name to query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Result limit"
                    }
                },
                "required": ["table"]
            },
            "tool_output_schema": {
                "type": "object",
                "properties": {
                    "rows": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                    "count": {
                        "type": "integer"
                    }
                }
            }
        }
        tool = DynamicTool(tool_asset)
        registry.register_dynamic(tool)

        info = registry.get_tool_info("detailed_tool")
        assert info["input_schema"]["properties"]["table"]["description"] == "Table name to query"
        assert info["output_schema"]["properties"]["rows"]["items"]["type"] == "object"

    def test_multiple_tools_info_independence(self):
        """Different tools should have independent schemas."""
        registry = ToolRegistry()

        # Tool A with specific schema
        tool_a_asset = {
            "name": "tool_a",
            "tool_type": "type_a",
            "tool_input_schema": {"properties": {"param_a": {"type": "string"}}}
        }
        # Tool B with different schema
        tool_b_asset = {
            "name": "tool_b",
            "tool_type": "type_b",
            "tool_input_schema": {"properties": {"param_b": {"type": "integer"}}}
        }

        registry.register_dynamic(DynamicTool(tool_a_asset))
        registry.register_dynamic(DynamicTool(tool_b_asset))

        info_a = registry.get_tool_info("tool_a")
        info_b = registry.get_tool_info("tool_b")

        assert "param_a" in info_a["input_schema"]["properties"]
        assert "param_b" in info_b["input_schema"]["properties"]
        assert "param_b" not in info_a["input_schema"]["properties"]
        assert "param_a" not in info_b["input_schema"]["properties"]


class TestGlobalToolRegistry:
    """Test global tool registry functions."""

    def test_global_registry_singleton(self):
        """get_tool_registry should return singleton."""
        reg1 = get_tool_registry()
        reg2 = get_tool_registry()
        assert reg1 is reg2

    def test_global_registry_info_methods(self):
        """Global registry should have info methods."""
        registry = get_tool_registry()
        assert hasattr(registry, "get_tool_info")
        assert hasattr(registry, "get_all_tools_info")
        assert hasattr(registry, "validate_tool_type")

    def test_global_registry_validate_tool_type(self):
        """Global registry validate_tool_type should work."""
        registry = get_tool_registry()
        # Note: This may fail if no tools are registered globally
        result = registry.validate_tool_type("nonexistent")
        assert isinstance(result, bool)
