"""
Advanced Query Decomposition Runner with state management,
recursive query decomposition, conditional branching, and dynamic tool composition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.config import AppSettings
from schemas import AnswerBlock, MarkdownBlock
from typing_extensions import TypedDict

from app.llm.client import get_llm_client, is_llm_available

# ============================================================================
# State Management
# ============================================================================


class ExecutionState(TypedDict):
    """Graph execution state with full context."""

    query: str
    original_query: str
    decomposed_queries: List[str]
    execution_path: List[str]
    results: Dict[str, Any]
    errors: List[str]
    metadata: Dict[str, Any]
    depth: int
    max_depth: int
    timestamp: str


class QueryType(str, Enum):
    """Types of queries that can be handled."""

    METRIC = "metric"
    GRAPH = "graph"
    HISTORY = "history"
    CI = "ci"
    COMPOSITE = "composite"
    RECURSIVE = "recursive"
    CONDITIONAL = "conditional"


class ExecutionMode(str, Enum):
    """Execution modes for the graph."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


# ============================================================================
# Query Analysis and Decomposition
# ============================================================================


@dataclass
class QueryAnalysis:
    """Analysis result for a query."""

    query_type: QueryType
    complexity: int  # 1-10 scale
    requires_decomposition: bool
    sub_queries: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    estimated_execution_time_ms: int = 0
    tools_needed: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


class QueryAnalyzer:
    """Analyzes queries to determine execution strategy."""

    def __init__(self, llm_client: Any, settings: AppSettings):
        self.llm_client = llm_client
        self.settings = settings

    def analyze(self, query: str, context: Dict[str, Any] = None) -> QueryAnalysis:
        """Analyze a query and return execution strategy."""
        context = context or {}

        # Detect query type
        query_type = self._detect_query_type(query)

        # Check if decomposition needed
        complexity = self._calculate_complexity(query)
        requires_decomposition = complexity > 5

        # Get sub-queries if needed
        sub_queries = []
        dependencies = {}
        if requires_decomposition:
            sub_queries, dependencies = self._decompose_query(query)

        # Determine tools needed
        tools_needed = self._determine_tools(query, query_type)

        # Extract conditions if conditional query
        conditions = {}
        if query_type == QueryType.CONDITIONAL:
            conditions = self._extract_conditions(query)

        return QueryAnalysis(
            query_type=query_type,
            complexity=complexity,
            requires_decomposition=requires_decomposition,
            sub_queries=sub_queries,
            dependencies=dependencies,
            tools_needed=tools_needed,
            conditions=conditions,
            estimated_execution_time_ms=self._estimate_execution_time(tools_needed),
        )

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query."""
        query_lower = query.lower()

        # Simple keyword-based detection
        if any(
            kw in query_lower for kw in ["metric", "measure", "count", "sum", "avg"]
        ):
            return QueryType.METRIC
        elif any(
            kw in query_lower
            for kw in ["relationship", "graph", "connect", "link", "node"]
        ):
            return QueryType.GRAPH
        elif any(
            kw in query_lower
            for kw in ["history", "log", "event", "change", "timeline"]
        ):
            return QueryType.HISTORY
        elif any(
            kw in query_lower for kw in ["ci", "configuration", "asset", "resource"]
        ):
            return QueryType.CI
        elif any(
            kw in query_lower for kw in ["if", "condition", "when", "case", "check"]
        ):
            return QueryType.CONDITIONAL
        elif "and" in query_lower or "or" in query_lower or "," in query:
            return QueryType.COMPOSITE
        else:
            return QueryType.METRIC

    def _calculate_complexity(self, query: str) -> int:
        """Calculate query complexity (1-10)."""
        complexity = 1

        # Length factor
        word_count = len(query.split())
        if word_count > 50:
            complexity += 3
        elif word_count > 30:
            complexity += 2
        elif word_count > 20:
            complexity += 1

        # Connector count (indicates composite queries)
        connector_count = query.lower().count(" and ") + query.lower().count(" or ")
        complexity += min(connector_count, 3)

        # Nested condition count
        paren_count = query.count("(")
        complexity += min(paren_count, 2)

        return min(complexity, 10)

    def _decompose_query(self, query: str) -> Tuple[List[str], Dict[str, List[str]]]:
        """Decompose a complex query into sub-queries."""
        # Split by connectors
        parts = []
        current = ""

        for char in query:
            if char in "(),;":
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip())

        # Further split by "and" and "or"
        sub_queries = []
        for part in parts:
            if " and " in part.lower():
                sub_queries.extend([p.strip() for p in part.split(" and ")])
            elif " or " in part.lower():
                sub_queries.extend([p.strip() for p in part.split(" or ")])
            else:
                sub_queries.append(part)

        # Build dependency graph
        dependencies = self._build_dependency_graph(sub_queries)

        return sub_queries, dependencies

    def _build_dependency_graph(self, queries: List[str]) -> Dict[str, List[str]]:
        """Build dependency graph for sub-queries."""
        dependencies = {q: [] for q in queries}

        # Simple heuristic: if a query mentions a result from another query
        for i, q1 in enumerate(queries):
            for j, q2 in enumerate(queries):
                if i != j:
                    # Check if q1 mentions elements from q2
                    words_q2 = set(q2.lower().split())
                    words_q1 = set(q1.lower().split())
                    if words_q2 & words_q1:
                        dependencies[q1].append(q2)

        return dependencies

    def _determine_tools(self, query: str, query_type: QueryType) -> List[str]:
        """Determine which tools are needed."""
        tools = []

        # Based on query type
        if query_type == QueryType.METRIC:
            tools.append("metric_executor")
        elif query_type == QueryType.GRAPH:
            tools.append("graph_executor")
        elif query_type == QueryType.HISTORY:
            tools.append("history_executor")
        elif query_type == QueryType.CI:
            tools.append("ci_executor")

        # Additional tools based on keywords
        if "recent" in query.lower() or "latest" in query.lower():
            if "history_executor" not in tools:
                tools.append("history_executor")

        if "trend" in query.lower():
            if "metric_executor" not in tools:
                tools.append("metric_executor")

        return tools

    def _extract_conditions(self, query: str) -> Dict[str, Any]:
        """Extract conditional logic from query."""
        conditions = {}

        # Simple extraction of if/then/else patterns
        if "if " in query.lower():
            parts = query.split(" if ")
            if len(parts) >= 2:
                conditions["type"] = "conditional"
                conditions["condition"] = (
                    parts[1].split(" then ")[0] if " then " in parts[1] else parts[1]
                )

        if "then" in query.lower():
            parts = query.split(" then ")
            if len(parts) >= 2:
                conditions["action"] = parts[1]

        if "else" in query.lower():
            parts = query.split(" else ")
            if len(parts) >= 2:
                conditions["alternative"] = parts[1]

        return conditions

    def _estimate_execution_time(self, tools: List[str]) -> int:
        """Estimate execution time in milliseconds."""
        base_time = 100  # Base overhead
        time_per_tool = 200  # Time per tool

        return base_time + (len(tools) * time_per_tool)


# ============================================================================
# Conditional Routing
# ============================================================================


class ConditionalRouter:
    """Routes execution based on conditions."""

    def __init__(self, llm_client: Any, settings: AppSettings):
        self.llm_client = llm_client
        self.settings = settings

    def should_execute(
        self,
        state: ExecutionState,
        tool: str,
        conditions: Dict[str, Any],
    ) -> bool:
        """Determine if a tool should be executed based on conditions."""
        # Check depth limit FIRST, before any condition checking
        if state["depth"] >= state["max_depth"]:
            return False

        if not conditions:
            return True

        # Check explicit conditions
        if "skip_if" in conditions:
            if self._evaluate_condition(state, conditions["skip_if"]):
                return False

        if "run_if" in conditions:
            if not self._evaluate_condition(state, conditions["run_if"]):
                return False

        return True

    def choose_path(
        self,
        state: ExecutionState,
        options: List[Tuple[str, Dict[str, Any]]],
    ) -> str:
        """Choose execution path based on state and conditions."""
        for option_name, conditions in options:
            if self.should_execute(state, option_name, conditions):
                return option_name

        # Return first option as default
        return options[0][0] if options else None

    def _evaluate_condition(self, state: ExecutionState, condition: str) -> bool:
        """Evaluate a condition against the state."""
        # Simple keyword-based evaluation
        condition_lower = condition.lower()

        if "error" in condition_lower:
            return len(state["errors"]) > 0

        if "empty" in condition_lower:
            return len(state["results"]) == 0

        if "complex" in condition_lower:
            return state["metadata"].get("complexity", 1) > 5

        return True


# ============================================================================
# Dynamic Tool Composition
# ============================================================================


class ToolComposer:
    """Composes tools dynamically based on query requirements."""

    def __init__(self):
        self.tool_registry: Dict[str, Callable] = {}
        self.composition_cache: Dict[str, List[str]] = {}

    def register_tool(self, name: str, executor: Callable) -> None:
        """Register a tool for use."""
        self.tool_registry[name] = executor

    def compose(self, tools_needed: List[str]) -> List[Callable]:
        """Compose a sequence of tools."""
        composed = []

        for tool_name in tools_needed:
            if tool_name in self.tool_registry:
                composed.append(self.tool_registry[tool_name])

        return composed

    def compose_with_dependencies(
        self,
        tools_needed: List[str],
        dependencies: Dict[str, List[str]],
    ) -> List[Tuple[str, List[str]]]:
        """Compose tools respecting dependencies."""
        # Build execution order based on dependencies
        executed = set()
        execution_order = []

        while len(executed) < len(tools_needed):
            made_progress = False

            for tool in tools_needed:
                if tool in executed:
                    continue

                # Check if all dependencies are met
                tool_deps = dependencies.get(tool, [])
                if all(dep in executed for dep in tool_deps):
                    execution_order.append((tool, tool_deps))
                    executed.add(tool)
                    made_progress = True

            if not made_progress:
                # Circular dependency or missing tool
                remaining = [t for t in tools_needed if t not in executed]
                execution_order.extend([(t, []) for t in remaining])
                break

        return execution_order


# ============================================================================
# Advanced Query Decomposition Runner with State Management
# ============================================================================


class QueryDecompositionRunner:
    """Advanced query decomposition runner with state management, recursion, and conditional branching."""

    def __init__(self, settings: AppSettings):
        if not is_llm_available(settings):
            raise ValueError("LLM provider is not configured")

        self.settings = settings
        self.llm_client = get_llm_client()
        self.analyzer = QueryAnalyzer(self.llm_client, settings)
        self.router = ConditionalRouter(self.llm_client, settings)
        self.composer = ToolComposer()
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        query: str,
        max_depth: int = 3,
        execution_mode: ExecutionMode = ExecutionMode.HYBRID,
    ) -> Tuple[List[AnswerBlock], List[str], Optional[str]]:
        """Run advanced query decomposition with state management and recursion."""

        try:
            # Initialize state
            state = ExecutionState(
                query=query,
                original_query=query,
                decomposed_queries=[],
                execution_path=[],
                results={},
                errors=[],
                metadata={"execution_mode": execution_mode.value},
                depth=0,
                max_depth=max_depth,
                timestamp=datetime.now().isoformat(),
            )

            # Analyze query
            analysis = self.analyzer.analyze(query)
            state["metadata"]["query_type"] = analysis.query_type.value
            state["metadata"]["complexity"] = analysis.complexity

            # Execute based on query type
            if analysis.requires_decomposition:
                state["decomposed_queries"] = analysis.sub_queries
                blocks, tools = self._execute_decomposed(
                    state, analysis, execution_mode
                )
            else:
                blocks, tools = self._execute_simple(state, analysis)

            # Build summary
            summary = self._build_summary(state, analysis, blocks)
            final_blocks = [summary] + blocks

            error_info = "; ".join(state["errors"]) if state["errors"] else None

            return final_blocks, tools, error_info

        except Exception as e:
            self.logger.exception("Query decomposition execution failed")
            error_block = MarkdownBlock(
                type="markdown",
                title="Execution Error",
                content=f"Failed to execute query: {str(e)}",
            )
            return [error_block], [], str(e)

    def _execute_simple(
        self,
        state: ExecutionState,
        analysis: QueryAnalysis,
    ) -> Tuple[List[AnswerBlock], List[str]]:
        """Execute a simple query."""
        blocks = []

        state["execution_path"].append(f"simple_{analysis.query_type.value}")

        # Create a markdown block with the analysis
        analysis_content = f"""
**Query Analysis:**
- Type: {analysis.query_type.value}
- Complexity: {analysis.complexity}/10
- Tools: {", ".join(analysis.tools_needed)}
- Estimated Time: {analysis.estimated_execution_time_ms}ms

**Execution Plan:**
Will execute {", ".join(analysis.tools_needed)} in sequence.
"""

        blocks.append(
            MarkdownBlock(
                type="markdown",
                title="Query Analysis",
                content=analysis_content,
            )
        )

        return blocks, analysis.tools_needed

    def _execute_decomposed(
        self,
        state: ExecutionState,
        analysis: QueryAnalysis,
        execution_mode: ExecutionMode,
    ) -> Tuple[List[AnswerBlock], List[str]]:
        """Execute a decomposed query recursively."""
        blocks = []
        all_tools = set()

        state["execution_path"].append(
            f"decomposed_{len(analysis.sub_queries)}_queries"
        )

        # Execute sub-queries
        for i, sub_query in enumerate(analysis.sub_queries):
            state["depth"] += 1

            if state["depth"] > state["max_depth"]:
                state["errors"].append(
                    f"Max recursion depth ({state['max_depth']}) reached"
                )
                break

            # Analyze sub-query
            sub_analysis = self.analyzer.analyze(sub_query, {"parent": state["query"]})

            # Check conditions before execution
            if not self.router.should_execute(
                state,
                f"sub_query_{i}",
                sub_analysis.conditions,
            ):
                continue

            # Execute sub-query
            state["results"][f"sub_query_{i}"] = {
                "query": sub_query,
                "type": sub_analysis.query_type.value,
                "tools": sub_analysis.tools_needed,
            }

            all_tools.update(sub_analysis.tools_needed)

        # Build execution summary
        summary_content = f"""
**Decomposed Execution:**
- Original Query: {state["original_query"]}
- Sub-queries: {len(analysis.sub_queries)}
- Execution Mode: {execution_mode.value}
- Depth: {state["depth"]}/{state["max_depth"]}
- Tools Used: {", ".join(sorted(all_tools)) if all_tools else "None"}

**Sub-query Results:**
"""

        for i, result in state["results"].items():
            summary_content += f"\n- {result['query']} → {result['type']}"

        blocks.append(
            MarkdownBlock(
                type="markdown",
                title="Decomposed Execution Summary",
                content=summary_content,
            )
        )

        return blocks, list(all_tools)

    def _build_summary(
        self,
        state: ExecutionState,
        analysis: QueryAnalysis,
        blocks: List[AnswerBlock],
    ) -> MarkdownBlock:
        """Build final summary block."""
        content = f"""
**Execution Summary:**
- Query: {state["original_query"]}
- Query Type: {analysis.query_type.value}
- Complexity: {analysis.complexity}/10
- Execution Path: {" → ".join(state["execution_path"])}
- Total Depth: {state["depth"]}/{state["max_depth"]}
- Timestamp: {state["timestamp"]}

**Results:**
- Sub-queries Executed: {len(state["results"])}
- Errors: {len(state["errors"])}

"""

        if state["errors"]:
            content += "\n**Errors:**\n"
            for error in state["errors"]:
                content += f"- {error}\n"

        return MarkdownBlock(
            type="markdown",
            title="Query Decomposition Execution Summary",
            content=content,
        )
