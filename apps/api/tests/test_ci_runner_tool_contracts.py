"""Test CI Runner Tool Contract implementation."""

from schemas.tool_contracts import ToolCall


class TestToolCallContract:
    """Test ToolCall Pydantic model."""

    def test_tool_call_creation(self):
        """Test creating a ToolCall instance."""
        tool_call = ToolCall(
            tool="ci.search",
            elapsed_ms=100,
            input_params={"keywords": ["test"]},
            output_summary={"rows": 5},
            error=None,
        )

        assert tool_call.tool == "ci.search"
        assert tool_call.elapsed_ms == 100
        assert tool_call.input_params == {"keywords": ["test"]}
        assert tool_call.output_summary == {"rows": 5}
        assert tool_call.error is None

    def test_tool_call_with_error(self):
        """Test creating a ToolCall with error."""
        tool_call = ToolCall(
            tool="ci.search",
            elapsed_ms=50,
            input_params={"keywords": []},
            output_summary={},
            error="Empty keywords",
        )

        assert tool_call.error == "Empty keywords"

    def test_tool_call_serialization(self):
        """Test ToolCall serialization to dict."""
        tool_call = ToolCall(
            tool="metric.aggregate",
            elapsed_ms=250,
            input_params={"metric": "cpu", "time_range": "24h"},
            output_summary={"value": 85.5},
            error=None,
        )

        call_dict = tool_call.model_dump()

        assert call_dict["tool"] == "metric.aggregate"
        assert call_dict["elapsed_ms"] == 250
        assert call_dict["input_params"] == {"metric": "cpu", "time_range": "24h"}
        assert call_dict["output_summary"] == {"value": 85.5}
        assert call_dict["error"] is None

    def test_tool_call_default_values(self):
        """Test ToolCall with default values."""
        tool_call = ToolCall(
            tool="graph.expand",
            elapsed_ms=500,
        )

        assert tool_call.input_params == {}
        assert tool_call.output_summary == {}
        assert tool_call.error is None


class TestToolCallTrace:
    """Test Tool Call Trace generation."""

    def test_multiple_tool_calls_accumulation(self):
        """Test accumulating multiple tool calls."""
        tool_calls = [
            ToolCall(
                tool="ci.search",
                elapsed_ms=100,
                input_params={"keywords": ["srv"]},
                output_summary={"rows": 10},
            ),
            ToolCall(
                tool="ci.get",
                elapsed_ms=50,
                input_params={"ci_id": "ci-1"},
                output_summary={"found": True},
            ),
            ToolCall(
                tool="graph.expand",
                elapsed_ms=300,
                input_params={"depth": 2},
                output_summary={"nodes": 25},
            ),
        ]

        # Verify accumulation
        assert len(tool_calls) == 3
        assert tool_calls[0].tool == "ci.search"
        assert tool_calls[1].tool == "ci.get"
        assert tool_calls[2].tool == "graph.expand"

        # Verify serialization
        serialized = [call.model_dump() for call in tool_calls]
        assert len(serialized) == 3
        assert serialized[0]["tool"] == "ci.search"
        assert serialized[1]["tool"] == "ci.get"
        assert serialized[2]["tool"] == "graph.expand"

    def test_tool_calls_with_errors(self):
        """Test tool calls including errors."""
        tool_calls = [
            ToolCall(
                tool="metric.aggregate",
                elapsed_ms=200,
                input_params={"metric": "cpu"},
                output_summary={"value": 85.0},
            ),
            ToolCall(
                tool="history.recent",
                elapsed_ms=100,
                input_params={"time_range": "7d"},
                output_summary={},
                error="Connection timeout",
            ),
        ]

        # Verify error handling
        assert tool_calls[0].error is None
        assert tool_calls[1].error == "Connection timeout"

        # Verify in serialization
        call_dicts = [call.model_dump() for call in tool_calls]
        assert call_dicts[0]["error"] is None
        assert call_dicts[1]["error"] == "Connection timeout"


class TestReferenceExtraction:
    """Test Reference extraction from blocks."""

    def test_extract_references_from_dict_blocks(self):
        """Test extracting references from dict-format blocks."""
        blocks = [
            {"type": "text", "text": "Some content"},
            {
                "type": "references",
                "items": [
                    {"kind": "sql", "title": "Query 1", "payload": "SELECT * FROM ci"},
                    {
                        "kind": "cypher",
                        "title": "Query 2",
                        "payload": "MATCH (n) RETURN n",
                    },
                ],
            },
        ]

        # Extract references
        references = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "references":
                items = block.get("items", [])
                for item in items:
                    if "kind" in item and "payload" in item:
                        references.append(item)

        # Verify extraction
        assert len(references) == 2
        assert references[0]["kind"] == "sql"
        assert references[0]["title"] == "Query 1"
        assert references[1]["kind"] == "cypher"
        assert references[1]["title"] == "Query 2"

    def test_no_references_in_blocks(self):
        """Test handling blocks without references."""
        blocks = [
            {"type": "text", "text": "Content"},
            {"type": "table", "rows": []},
        ]

        references = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "references":
                items = block.get("items", [])
                for item in items:
                    if "kind" in item and "payload" in item:
                        references.append(item)

        assert len(references) == 0

    def test_multiple_reference_blocks(self):
        """Test extracting references from multiple reference blocks."""
        blocks = [
            {
                "type": "references",
                "items": [
                    {"kind": "sql", "title": "Query 1", "payload": "SELECT ..."},
                ],
            },
            {"type": "text", "text": "Middle content"},
            {
                "type": "references",
                "items": [
                    {"kind": "cypher", "title": "Query 2", "payload": "MATCH ..."},
                    {"kind": "sql", "title": "Query 3", "payload": "SELECT ..."},
                ],
            },
        ]

        references = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "references":
                items = block.get("items", [])
                for item in items:
                    if "kind" in item and "payload" in item:
                        references.append(item)

        assert len(references) == 3
        assert references[0]["kind"] == "sql"
        assert references[1]["kind"] == "cypher"
        assert references[2]["kind"] == "sql"
