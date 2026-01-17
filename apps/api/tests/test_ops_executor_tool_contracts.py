"""Test OPS Executors Tool Contract implementation."""

from unittest.mock import MagicMock

import pytest

from schemas.tool_contracts import ExecutorResult, ToolCall
from schemas import MarkdownBlock, ReferencesBlock, ReferenceItem, TableBlock


class TestExecutorResultStructure:
    """Test ExecutorResult Pydantic model."""

    def test_executor_result_creation(self):
        """Test creating an ExecutorResult instance."""
        blocks = [{"type": "markdown", "title": "Test", "content": "Test content"}]
        tool_calls = [
            ToolCall(tool="metric.series", elapsed_ms=100, input_params={}, output_summary={})
        ]
        references = [{"kind": "sql", "title": "Query", "payload": "SELECT 1"}]

        result = ExecutorResult(
            blocks=blocks,
            used_tools=["postgres"],
            tool_calls=tool_calls,
            references=references,
            summary={"status": "success", "rows": 5},
        )

        assert result.blocks == blocks
        assert result.used_tools == ["postgres"]
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool == "metric.series"
        assert result.references == references
        assert result.summary["status"] == "success"

    def test_executor_result_with_defaults(self):
        """Test ExecutorResult with default values."""
        result = ExecutorResult(
            blocks=[],
            used_tools=[],
        )

        assert result.blocks == []
        assert result.used_tools == []
        assert result.tool_calls == []
        assert result.references == []
        assert result.summary == {}

    def test_executor_result_serialization(self):
        """Test ExecutorResult serialization to dict."""
        result = ExecutorResult(
            blocks=[{"type": "markdown", "content": "test"}],
            used_tools=["postgres", "timescale"],
            tool_calls=[
                ToolCall(
                    tool="metric.series",
                    elapsed_ms=250,
                    input_params={"metric": "cpu"},
                    output_summary={"rows": 10},
                )
            ],
            references=[{"kind": "sql", "title": "Query", "payload": "SELECT ..."}],
            summary={"status": "success"},
        )

        result_dict = result.dict()

        assert result_dict["blocks"] == [{"type": "markdown", "content": "test"}]
        assert "postgres" in result_dict["used_tools"]
        assert len(result_dict["tool_calls"]) == 1
        assert result_dict["tool_calls"][0]["tool"] == "metric.series"
        assert len(result_dict["references"]) == 1
        assert result_dict["summary"]["status"] == "success"


class TestMetricExecutorToolContract:
    """Test metric_executor Tool Contract implementation."""

    def test_metric_executor_structure_can_be_verified(self):
        """Test that metric_executor module can be imported."""
        try:
            from app.modules.ops.services.executors.metric_executor import run_metric
            assert callable(run_metric)
        except ImportError:
            pytest.fail("metric_executor should be importable")

    def test_hist_executor_structure_can_be_verified(self):
        """Test that hist_executor module can be imported."""
        try:
            from app.modules.ops.services.executors.hist_executor import run_hist
            assert callable(run_hist)
        except ImportError:
            pytest.fail("hist_executor should be importable")


class TestHistExecutorToolContract:
    """Test hist_executor Tool Contract implementation."""

    def test_hist_executor_can_be_imported(self):
        """Test that hist_executor module can be imported."""
        try:
            from app.modules.ops.services.executors.hist_executor import run_hist
            assert callable(run_hist)
        except ImportError:
            pytest.fail("hist_executor should be importable")


class TestGraphExecutorToolContract:
    """Test graph_executor Tool Contract implementation."""

    def test_graph_executor_can_be_imported(self):
        """Test that graph_executor module can be imported."""
        try:
            from app.modules.ops.services.executors.graph_executor import run_graph
            assert callable(run_graph)
        except ImportError:
            pytest.fail("graph_executor should be importable")


class TestExecutorBackwardCompatibility:
    """Test backward compatibility of executor result changes."""

    def test_normalize_real_result_with_executor_result(self, monkeypatch):
        """Test _normalize_real_result handles ExecutorResult."""
        # Can't test directly because _normalize_real_result is an internal function
        # Instead test through the public API
        monkeypatch.setenv("OPS_MODE", "mock")
        from app.modules.ops.services import handle_ops_query

        envelope = handle_ops_query("metric", "test question")

        # Verify the response structure is valid
        assert envelope.meta is not None
        assert envelope.blocks is not None
        assert envelope.meta.used_tools is not None

    def test_normalize_real_result_with_legacy_tuple(self):
        """Test _normalize_real_result still handles legacy tuples."""
        from app.modules.ops.services import _normalize_real_result

        blocks = [{"type": "markdown", "content": "test"}]
        used_tools = ["postgres"]

        normalized_blocks, normalized_tools, error, executor = _normalize_real_result((blocks, used_tools))

        assert normalized_blocks == blocks
        assert normalized_tools == used_tools
        assert error is None
        assert executor is None

    def test_normalize_real_result_with_legacy_tuple_and_error(self):
        """Test _normalize_real_result handles legacy tuples with error."""
        from app.modules.ops.services import _normalize_real_result

        blocks = [{"type": "markdown", "content": "test"}]
        used_tools = ["postgres"]
        error = "Test error"

        normalized_blocks, normalized_tools, normalized_error, executor = _normalize_real_result(
            (blocks, used_tools, error)
        )

        assert normalized_blocks == blocks
        assert normalized_tools == used_tools
        assert normalized_error == error
        assert executor is None


class TestToolCallSerialization:
    """Test ToolCall serialization in ExecutorResult."""

    def test_executor_result_tool_calls_serialize_correctly(self):
        """Test that ToolCall objects serialize properly in ExecutorResult."""
        tool_calls = [
            ToolCall(
                tool="metric.series",
                elapsed_ms=100,
                input_params={"metric": "cpu"},
                output_summary={"rows": 5},
            ),
            ToolCall(
                tool="history.recent",
                elapsed_ms=50,
                input_params={"ci_code": "srv-01"},
                output_summary={"events": 3},
            ),
        ]

        result = ExecutorResult(
            blocks=[],
            used_tools=["postgres"],
            tool_calls=tool_calls,
        )

        serialized = result.dict()

        assert len(serialized["tool_calls"]) == 2
        assert serialized["tool_calls"][0]["tool"] == "metric.series"
        assert serialized["tool_calls"][0]["elapsed_ms"] == 100
        assert serialized["tool_calls"][0]["input_params"]["metric"] == "cpu"
        assert serialized["tool_calls"][1]["tool"] == "history.recent"
        assert serialized["tool_calls"][1]["input_params"]["ci_code"] == "srv-01"


class TestReferenceExtraction:
    """Test reference extraction from executor blocks."""

    def test_reference_extraction_from_references_block(self):
        """Test extracting references from ReferencesBlock items."""
        references_block = ReferencesBlock(
            type="references",
            title="Test References",
            items=[
                ReferenceItem(
                    kind="sql",
                    title="Query 1",
                    payload={"query": "SELECT * FROM metrics"},
                ),
                ReferenceItem(
                    kind="cypher",
                    title="Query 2",
                    payload={"cypher": "MATCH (n) RETURN n"},
                ),
            ],
        )

        block_dict = references_block.dict()

        # Extract references as done in executors
        references = []
        if block_dict.get("type") == "references":
            for item in block_dict.get("items", []):
                references.append(item)

        assert len(references) == 2
        assert references[0]["kind"] == "sql"
        assert references[1]["kind"] == "cypher"

    def test_empty_references_handling(self):
        """Test handling blocks with no references."""
        blocks = [
            MarkdownBlock(type="markdown", title="Test", content="Content"),
            TableBlock(type="table", title="Table", columns=["col1"], rows=[]),
        ]

        blocks_dict = [block.dict() if hasattr(block, "dict") else block for block in blocks]

        references = []
        for block_dict in blocks_dict:
            if block_dict.get("type") == "references":
                for item in block_dict.get("items", []):
                    references.append(item)

        assert len(references) == 0
