"""Tool Orchestration Layer for dynamic execution planning.

This module implements orchestration capabilities to translate Plan objects
into executable tool chains with support for:
- Parallel execution for independent tools
- Serial execution for dependent tools
- DAG-based execution for complex dependencies
- Data flow mapping between tool outputs and inputs
- Intermediate LLM decision points for dynamic branching
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Optional, Set

from core.logging import get_logger

from app.llm.client import get_llm_client
from app.modules.ops.services.ci.orchestrator.chain_executor import (
    ToolChain,
    ToolChainExecutor,
    ToolChainStep,
)
from app.modules.ops.services.ci.planner.plan_schema import (
    ExecutionStrategy,
    Plan,
    ToolDependency,
)
from app.modules.ops.services.ci.tools.base import ToolContext

logger = get_logger(__name__)


class DependencyAnalyzer:
    """Analyze Plan to extract tool dependencies and build execution DAG."""

    def extract_dependencies(self, plan: Plan) -> List[ToolDependency]:
        """Extract tool dependencies from Plan.

        If explicit dependencies provided, use them.
        Otherwise, infer dependencies from Plan structure.
        """
        # If explicit dependencies provided, use them
        if plan.tool_dependencies:
            return plan.tool_dependencies

        # Otherwise, infer from Plan structure
        dependencies = self._infer_dependencies_from_plan(plan)
        return dependencies

    def _infer_dependencies_from_plan(self, plan: Plan) -> List[ToolDependency]:
        """Infer tool dependencies from Plan structure.

        Infers the following dependency pattern:
        - primary: no dependencies (entry point)
        - secondary: no dependencies (independent)
        - aggregate: depends on primary (needs ci_type filter)
        - graph: depends on primary (needs ci_id)
        - metric: can depend on aggregate (refinement)
        """
        deps = []

        # Primary tool (no dependencies)
        if plan.primary and plan.primary.keywords:
            deps.append(ToolDependency(
                tool_id="primary",
                depends_on=[],
            ))

        # Secondary tool (independent of primary)
        if plan.secondary and plan.secondary.keywords:
            deps.append(ToolDependency(
                tool_id="secondary",
                depends_on=[],
            ))

        # Aggregate depends on primary (needs ci_type filter from primary results)
        if plan.aggregate:
            primary_deps = ["primary"] if plan.primary else []
            deps.append(ToolDependency(
                tool_id="aggregate",
                depends_on=primary_deps,
                output_mapping={
                    "ci_type_filter": "primary.data.rows[0].ci_type"
                } if plan.primary else {}
            ))

        # Metric can depend on aggregate or primary (ci_lookup with metric data)
        if plan.metric:
            # Prefer ci_lookup (primary) as it already has metric data, fallback to aggregate
            metric_deps = ["primary"] if plan.primary else (["aggregate"] if plan.aggregate else [])
            ci_source = "primary" if plan.primary else ("aggregate" if plan.aggregate else None)
            deps.append(ToolDependency(
                tool_id="metric",
                depends_on=metric_deps,
                output_mapping={
                    "ci_ids": f"{ci_source}.data.rows.*.ci_id"
                } if ci_source else {}
            ))

        # History depends on primary or metric (needs ci_id from results)
        # Prefer primary to avoid NULL when metric rows are empty
        if plan.history and plan.history.enabled:
            if plan.primary:
                # History depends on primary results
                deps.append(ToolDependency(
                    tool_id="history",
                    depends_on=["primary"],
                    output_mapping={
                        "ci_id": "primary.data.rows[0].ci_id"
                    }
                ))
            elif plan.metric:
                # History depends on metric results
                deps.append(ToolDependency(
                    tool_id="history",
                    depends_on=["metric"],
                    output_mapping={
                        "ci_id": "metric.data.rows[0].ci_id"
                    }
                ))
            else:
                # History is independent
                deps.append(ToolDependency(
                    tool_id="history",
                    depends_on=[],
                ))

        # Graph depends on primary (needs ci_id from primary results)
        # NOTE: keep graph last to avoid blocking other tools in serial execution.
        if plan.graph:
            primary_deps = ["primary"] if plan.primary else []
            deps.append(ToolDependency(
                tool_id="graph",
                depends_on=primary_deps,
                output_mapping={
                    "root_ci_id": "primary.data.rows[0].ci_id"
                } if plan.primary else {}
            ))

        return deps

    def build_dependency_graph(self, dependencies: List[ToolDependency]) -> Dict[str, Set[str]]:
        """Build dependency graph as adjacency list.

        Returns:
            Dict mapping tool_id -> Set of tool_ids it depends on
        """
        graph = {}
        for dep in dependencies:
            graph[dep.tool_id] = set(dep.depends_on)
        return graph

    def topological_sort(self, dependencies: List[ToolDependency]) -> List[str]:
        """Perform topological sort on dependencies.

        Returns:
            List of tool_ids in execution order
        """
        graph = self.build_dependency_graph(dependencies)
        in_degree = {tool: len(deps) for tool, deps in graph.items()}
        queue = [tool for tool, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Find tools that depend on current
            for tool, deps in graph.items():
                if current in deps:
                    in_degree[tool] -= 1
                    if in_degree[tool] == 0:
                        queue.append(tool)

        if len(result) != len(graph):
            raise ValueError("Circular dependency detected in tool dependencies")

        return result


class DataFlowMapper:
    """Map tool outputs to inputs based on output_mapping specifications."""

    def resolve_mapping(
        self,
        output_mapping: Dict[str, str],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve output_mapping references to actual values.

        Args:
            output_mapping: Map of {input_field: reference_string}
            previous_results: Results from previous tool executions

        Returns:
            Dict mapping input_field to resolved values
        """
        resolved = {}

        for input_field, reference in output_mapping.items():
            # Reference format: "{tool_id}.output.field.path" or literal value
            if reference.startswith("{") and reference.endswith("}"):
                ref = reference[1:-1]  # Remove braces
                value = self._resolve_reference(ref, previous_results)
                resolved[input_field] = value
            else:
                # Literal value
                resolved[input_field] = reference

        return resolved

    def _resolve_reference(self, reference: str, results: Dict[str, Any]) -> Any:
        """Resolve JSONPath-like reference to value.

        Reference format: "tool_id.data.rows[0].field.subfield"
        """
        parts = reference.split(".")
        tool_id = parts[0]

        if tool_id not in results:
            logger.warning(f"Tool {tool_id} not found in results")
            return None

        value = results[tool_id]

        for part in parts[1:]:
            if "[" in part and "]" in part:
                # Handle array indexing: "rows[0]"
                base, index_str = part.split("[")
                index = int(index_str.rstrip("]"))

                if isinstance(value, dict) and base:
                    value = value.get(base)
                    if isinstance(value, list):
                        value = value[index] if index < len(value) else None
                elif isinstance(value, list):
                    value = value[index] if index < len(value) else None
                else:
                    logger.warning(f"Cannot index {part} in {reference}")
                    return None
            else:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    logger.warning(f"Cannot resolve {part} in {reference}")
                    return None

            if value is None:
                return None

        return value


class ExecutionPlanner:
    """Determine optimal execution strategy (parallel/serial/dag)."""

    def determine_strategy(self, dependencies: List[ToolDependency]) -> ExecutionStrategy:
        """Determine optimal execution strategy.

        Logic:
        - If all independent (no depends_on): PARALLEL
        - If complex DAG (multiple entry points that converge): DAG
        - If simple chain: SERIAL
        """
        if not dependencies:
            return ExecutionStrategy.SERIAL

        # Check if any dependencies exist
        has_dependencies = any(dep.depends_on for dep in dependencies)

        if not has_dependencies:
            # All independent → parallel
            return ExecutionStrategy.PARALLEL

        # Check for complex DAG
        if self._has_complex_dag(dependencies):
            return ExecutionStrategy.DAG

        # Simple chain → serial
        return ExecutionStrategy.SERIAL

    def _has_complex_dag(self, dependencies: List[ToolDependency]) -> bool:
        """Check if dependencies form a complex DAG.

        Complex if:
        - Multiple independent branches (entry points > 1) that converge
        - Or single tool depends on multiple other tools
        """
        dependency_graph = {dep.tool_id: dep.depends_on for dep in dependencies}

        # Count tools with no dependencies (entry points)
        entry_points = sum(1 for deps in dependency_graph.values() if not deps)

        # Check for convergence (tool with multiple dependencies)
        has_convergence = any(len(deps) > 1 for deps in dependency_graph.values())

        return (entry_points > 1 and has_convergence) or any(len(deps) > 1 for deps in dependency_graph.values())

    def create_execution_groups(
        self,
        dependencies: List[ToolDependency],
        strategy: ExecutionStrategy
    ) -> List[List[str]]:
        """Create groups of tools that can execute together.

        For PARALLEL: all tools in one group
        For SERIAL: one tool per group (in dependency order)
        For DAG: group by execution level
        """
        if strategy == ExecutionStrategy.PARALLEL:
            # All tools can execute together
            return [[dep.tool_id for dep in dependencies]]

        elif strategy == ExecutionStrategy.SERIAL:
            # One per group in dependency order
            analyzer = DependencyAnalyzer()
            sorted_tools = analyzer.topological_sort(dependencies)
            return [[tool] for tool in sorted_tools]

        elif strategy == ExecutionStrategy.DAG:
            # Group by level in DAG
            return self._group_by_dag_level(dependencies)

        return [[dep.tool_id for dep in dependencies]]

    def _group_by_dag_level(self, dependencies: List[ToolDependency]) -> List[List[str]]:
        """Group tools by execution level in DAG."""
        graph = {dep.tool_id: dep.depends_on for dep in dependencies}
        levels: Dict[str, int] = {}

        # Assign level to each tool
        def get_level(tool_id: str) -> int:
            if tool_id in levels:
                return levels[tool_id]

            deps = graph.get(tool_id, [])
            if not deps:
                levels[tool_id] = 0
                return 0

            level = max(get_level(dep) for dep in deps) + 1
            levels[tool_id] = level
            return level

        # Calculate levels for all tools
        for tool_id in graph:
            get_level(tool_id)

        # Group by level
        max_level = max(levels.values()) if levels else 0
        groups = [[] for _ in range(max_level + 1)]

        for tool_id, level in levels.items():
            groups[level].append(tool_id)

        return groups


class IntermediateLLMDecider:
    """Make intermediate decisions using LLM between tool executions."""

    def __init__(self):
        self.llm_client = get_llm_client()

    async def should_execute_next(
        self,
        tool_id: str,
        previous_results: Dict[str, Any],
        original_question: str
    ) -> bool:
        """Ask LLM if next tool should execute based on previous results.

        Args:
            tool_id: ID of next tool to potentially execute
            previous_results: Results from previous tool executions
            original_question: Original user question

        Returns:
            True if tool should execute, False otherwise
        """
        prompt = self._build_decision_prompt(tool_id, previous_results, original_question)

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                temperature=0.0,
            )

            decision = response.get("content", "").strip().lower()
            return decision.startswith("yes")
        except Exception as e:
            logger.warning(f"LLM decision failed for {tool_id}: {e}, defaulting to True")
            return True

    def _build_decision_prompt(
        self,
        tool_id: str,
        previous_results: Dict[str, Any],
        original_question: str
    ) -> str:
        """Build prompt for intermediate LLM decision."""
        formatted_results = self._format_results(previous_results)

        return f"""You are an intelligent query orchestrator. Based on the results so far, decide if we should execute the next tool.

Original Question: {original_question}

Previous Results:
{formatted_results}

Next Tool: {tool_id}

Should we execute {tool_id}? Answer 'Yes' or 'No' with brief reasoning.
"""

    def _format_results(self, results: Dict[str, Any]) -> str:
        """Format results for LLM consumption."""
        formatted = []
        for tool_id, result in results.items():
            if isinstance(result, dict):
                row_count = len(result.get("data", {}).get("rows", []))
                formatted.append(f"- {tool_id}: {row_count} rows")
            else:
                formatted.append(f"- {tool_id}: {type(result).__name__}")
        return "\n".join(formatted) if formatted else "No previous results"


class ToolOrchestrator:
    """Main orchestration layer coordinating all components."""

    def __init__(self, plan: Plan, context: ToolContext):
        """Initialize orchestrator with plan and context.

        Args:
            plan: Execution plan with tool specifications
            context: Tool execution context (trace_id, assets, params, etc.)
        """
        self.plan = plan
        self.context = context
        self.dependency_analyzer = DependencyAnalyzer()
        self.data_flow_mapper = DataFlowMapper()
        self.execution_planner = ExecutionPlanner()
        self.llm_decider = IntermediateLLMDecider() if plan.enable_intermediate_llm else None
        # Use get_chain_executor() to get the global executor which has proper registry
        from app.modules.ops.services.ci.orchestrator.chain_executor import get_chain_executor
        self.chain_executor = get_chain_executor()
        self.start_time = perf_counter()

    async def execute(self, execution_plan_trace: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute orchestrated tool execution.

        Flow:
        1. Analyze dependencies from plan
        2. Determine execution strategy
        3. Build ToolChain from dependencies
        4. Execute with ToolChainExecutor

        Args:
            execution_plan_trace: Optional execution plan metadata for trace integration

        Returns:
            Dict mapping tool_id -> execution result
        """
        try:
            # Step 1: Analyze dependencies
            dependencies = self.dependency_analyzer.extract_dependencies(self.plan)
            logger.info(
                "orchestration.dependencies_extracted",
                extra={
                    "count": len(dependencies),
                    "trace_id": self.context.trace_id
                }
            )

            # Step 2: Determine execution strategy
            strategy = self.execution_planner.determine_strategy(dependencies)
            logger.info(
                "orchestration.strategy_determined",
                extra={
                    "strategy": strategy.value,
                    "trace_id": self.context.trace_id
                }
            )

            # Step 3: Build ToolChain with execution plan trace
            execution_plan_trace = execution_plan_trace or self._create_execution_plan_trace(
                dependencies, strategy
            )
            tool_chain = self._build_tool_chain(dependencies, strategy)
            tool_chain.metadata = execution_plan_trace
            logger.info(
                "orchestration.tool_chain_built",
                extra={
                    "steps": len(tool_chain.steps),
                    "trace_id": self.context.trace_id
                }
            )

            # Step 4: Execute with ToolChainExecutor
            chain_result = await self.chain_executor.execute_chain(
                tool_chain, self.context, execution_plan_trace=execution_plan_trace
            )

            elapsed = int((perf_counter() - self.start_time) * 1000)
            logger.info(
                "orchestration.execution_completed",
                extra={
                    "elapsed_ms": elapsed,
                    "tool_count": len(chain_result.step_results),
                    "success": chain_result.success,
                    "trace_id": self.context.trace_id
                }
            )

            return chain_result

        except Exception as e:
            elapsed = int((perf_counter() - self.start_time) * 1000)
            logger.error(
                "orchestration.execution_failed",
                extra={
                    "error": str(e),
                    "elapsed_ms": elapsed,
                    "trace_id": self.context.trace_id
                }
            )
            raise

    def _build_tool_chain(
        self,
        dependencies: List[ToolDependency],
        strategy: ExecutionStrategy
    ) -> ToolChain:
        """Build ToolChain from dependencies.

        Creates ToolChainStep for each tool with:
        - Tool type and parameters from Plan
        - Dependencies information
        - Data flow mappings
        - Conditional execution rules
        """
        steps = []

        for dep in dependencies:
            # Get tool spec from plan
            tool_spec = self._get_tool_spec_by_id(dep.tool_id)
            if not tool_spec:
                logger.warning(f"Could not find spec for tool {dep.tool_id}")
                continue

            # Create ToolChainStep
            step = ToolChainStep(
                step_id=dep.tool_id,
                tool_name=tool_spec["tool_type"],
                parameters=tool_spec["params"],
                depends_on=dep.depends_on,
                output_mapping=dep.output_mapping,
            )
            steps.append(step)

        return ToolChain(
            chain_id=f"plan_{self.plan.intent.value if self.plan.intent else 'unknown'}",
            execution_mode=strategy.value,
            steps=steps,
        )

    def _get_tool_spec_by_id(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool specification from Plan by tool_id.

        Returns:
            Dict with tool_type and params, or None if not found
        """
        # Map tool_id to Plan spec attributes
        spec_map = {
            "primary": self.plan.primary,
            "secondary": self.plan.secondary,
            "aggregate": self.plan.aggregate,
            "graph": self.plan.graph,
            "metric": self.plan.metric,
            "history": self.plan.history,
        }

        spec_obj = spec_map.get(tool_id)
        if spec_obj:
            return self._extract_tool_spec(tool_id, spec_obj)

        return None

    def _extract_tool_spec(self, tool_id: str, spec_obj: Any) -> Dict[str, Any]:
        """Extract tool specification from spec object.

        Extracts tool_type and relevant parameters based on the spec type.
        The tool_type is now dynamically retrieved from the Plan spec object,
        allowing for flexible tool selection at runtime instead of hardcoding.

        Args:
            tool_id: Identifier of the tool (primary, secondary, aggregate, graph, metric)
            spec_obj: The spec object from the Plan containing tool_type and parameters

        Returns:
            Dict with tool_type and params, or None if tool_id not recognized
        """
        tool_type = getattr(spec_obj, 'tool_type', 'unknown')

        if tool_id == "primary":
            return {
                "tool_type": tool_type,
                "params": {
                    "keywords": spec_obj.keywords,
                    "filters": spec_obj.filters,
                    "limit": spec_obj.limit,
                }
            }
        elif tool_id == "secondary":
            return {
                "tool_type": tool_type,
                "params": {
                    "keywords": spec_obj.keywords,
                    "filters": spec_obj.filters,
                    "limit": spec_obj.limit,
                }
            }
        elif tool_id == "aggregate":
            return {
                "tool_type": tool_type,
                "params": {
                    "group_by": spec_obj.group_by,
                    "metrics": spec_obj.metrics,
                    "filters": spec_obj.filters,
                    "top_n": spec_obj.top_n,
                    "limit": spec_obj.top_n or 10,  # Map top_n to limit for query template
                    "scope": spec_obj.scope,
                    "tenant_id": self.context.tenant_id,  # Add tenant_id for query template
                }
            }
        elif tool_id == "graph":
            return {
                "tool_type": tool_type,
                "params": {
                    "depth": spec_obj.depth,
                    "view": spec_obj.view,
                    "limits": spec_obj.limits.model_dump() if hasattr(spec_obj.limits, 'model_dump') else spec_obj.limits,
                }
            }
        elif tool_id == "metric":
            # Convert time_range to start_time and end_time
            from datetime import datetime, timedelta
            end_time = datetime.utcnow()
            time_range = spec_obj.time_range
            if time_range in {"all_time", "all"} or self.context.get_metadata("full_time_range"):
                start_time = datetime(1970, 1, 1)
            elif time_range == "last_24h":
                start_time = end_time - timedelta(hours=24)
            elif time_range == "last_7d":
                start_time = end_time - timedelta(days=7)
            elif time_range == "last_30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(hours=24)

            return {
                "tool_type": tool_type,
                "params": {
                    "metric_name": spec_obj.metric_name,
                    "agg": spec_obj.agg,
                    "time_range": spec_obj.time_range,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "mode": getattr(spec_obj, 'mode', 'aggregate'),
                    "tenant_id": self.context.tenant_id,
                    "ci_ids": [],  # Will be populated from dependencies
                    "limit": 10,  # Return top 10 CIs by metric value
                }
            }
        elif tool_id == "history":
            # Convert time_range to start_time and end_time
            from datetime import datetime, timedelta
            end_time = datetime.utcnow()
            time_range = spec_obj.time_range
            if time_range in {"all_time", "all"}:
                start_time = datetime(1970, 1, 1)
            elif time_range == "last_24h":
                start_time = end_time - timedelta(hours=24)
            elif time_range == "last_7d":
                start_time = end_time - timedelta(days=7)
            elif time_range == "last_30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)  # default for history

            return {
                "tool_type": tool_type,
                "params": {
                    "source": spec_obj.source,
                    "scope": spec_obj.scope,
                    "mode": spec_obj.mode,
                    "time_range": spec_obj.time_range,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "limit": spec_obj.limit,
                    "tenant_id": self.context.tenant_id,
                    "ci_id": None,  # Will be populated from dependencies
                }
            }

        return None

    def _create_execution_plan_trace(
        self,
        dependencies: List[ToolDependency],
        strategy: ExecutionStrategy
    ) -> Dict[str, Any]:
        """Create trace metadata for execution plan.

        Generates execution plan metadata including:
        - Execution strategy (PARALLEL/SERIAL/DAG)
        - Execution groups (tools that execute together)
        - Dependency information for each tool
        - Tool type mapping

        Args:
            dependencies: Extracted tool dependencies
            strategy: Determined execution strategy

        Returns:
            Dict containing execution plan trace metadata
        """
        try:
            # Create execution groups based on strategy
            execution_groups = self.execution_planner.create_execution_groups(dependencies, strategy)

            # Build group information with dependency tracking
            groups_info = []
            for group_index, group_tools in enumerate(execution_groups):
                group_info = {
                    "group_index": group_index,
                    "tools": [],
                    "parallel_execution": len(group_tools) > 1,
                }

                for tool_id in group_tools:
                    # Find dependency info for this tool
                    tool_deps = next((d for d in dependencies if d.tool_id == tool_id), None)
                    depends_on = tool_deps.depends_on if tool_deps else []

                    # Get dependency groups
                    dependency_groups = self._get_dependency_groups(group_index, execution_groups, dependencies)

                    tool_info = {
                        "tool_id": tool_id,
                        "tool_type": self._get_tool_type(tool_id),
                        "depends_on": depends_on,
                        "dependency_groups": dependency_groups,
                        "output_mapping": tool_deps.output_mapping if tool_deps else {},
                    }
                    group_info["tools"].append(tool_info)

                groups_info.append(group_info)

            # Build execution plan trace
            execution_plan_trace = {
                "strategy": strategy.value,
                "execution_groups": groups_info,
                "total_groups": len(execution_groups),
                "total_tools": len(dependencies),
                "tool_ids": [dep.tool_id for dep in dependencies],
            }

            logger.info(
                "orchestration.execution_plan_trace_created",
                extra={
                    "strategy": strategy.value,
                    "total_groups": len(execution_groups),
                    "total_tools": len(dependencies),
                    "trace_id": self.context.trace_id
                }
            )

            return execution_plan_trace

        except Exception as e:
            logger.error(
                "orchestration.execution_plan_trace_creation_failed",
                extra={
                    "error": str(e),
                    "trace_id": self.context.trace_id
                }
            )
            # Return minimal trace on error
            return {
                "strategy": strategy.value,
                "execution_groups": [],
                "total_groups": 0,
                "total_tools": len(dependencies),
                "error": str(e),
            }

    def _get_dependency_groups(
        self,
        group_index: int,
        groups: List[List[str]],
        dependencies: List[ToolDependency]
    ) -> List[int]:
        """Get which groups a tool group depends on.

        Args:
            group_index: Index of current group
            groups: All execution groups
            dependencies: Tool dependencies

        Returns:
            List of group indices that this group depends on
        """
        if group_index == 0:
            return []

        current_group_tools = groups[group_index]
        dependency_groups = set()

        for tool_id in current_group_tools:
            tool_dep = next((d for d in dependencies if d.tool_id == tool_id), None)
            if tool_dep:
                for depends_on_tool in tool_dep.depends_on:
                    # Find which group this dependency is in
                    for prev_group_idx, prev_group_tools in enumerate(groups[:group_index]):
                        if depends_on_tool in prev_group_tools:
                            dependency_groups.add(prev_group_idx)
                            break

        return sorted(list(dependency_groups))

    def _get_tool_type(self, tool_id: str) -> str:
        """Get tool type for a tool_id.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool type string
        """
        tool_spec = self._get_tool_spec_by_id(tool_id)
        if tool_spec:
            return tool_spec.get("tool_type", "unknown")
        return "unknown"
