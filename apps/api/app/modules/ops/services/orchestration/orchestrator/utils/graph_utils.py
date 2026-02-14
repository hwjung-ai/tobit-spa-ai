"""Graph utilities for orchestration.

This module handles graph-related intent detection and fallthrough logic.
"""


from app.modules.ops.services.orchestration.planner.plan_schema import Intent, View


def is_graph_requested(
    plan_graph_view: View | None,
    plan_view: View | None,
    plan_output_blocks: list[str] | None,
) -> bool:
    """Check if user requested graph visualization.

    Args:
        plan_graph_view: Graph view from plan
        plan_view: Default view from plan
        plan_output_blocks: Output blocks from plan

    Returns:
        True if graph is requested
    """
    view = plan_graph_view or plan_view or View.SUMMARY

    if view in {
        View.COMPOSITION,
        View.DEPENDENCY,
        View.IMPACT,
        View.NEIGHBORS,
        View.PATH,
    }:
        return True

    return "network" in (plan_output_blocks or [])


def should_list_fallthrough_to_lookup(
    plan_intent: Intent,
    plan_list_enabled: bool,
    graph_requested: bool,
    has_ci_identifier: bool,
) -> bool:
    """Check if list results should fall through to CI lookup with graph.

    This is used when:
    - User requested a list
    - But also requested a graph
    - And provided CI identifiers
    Then we fall through to CI lookup to get detail for graph.

    Args:
        plan_intent: Intent from plan
        plan_list_enabled: Whether list is enabled in plan
        graph_requested: Whether graph is requested
        has_ci_identifier: Whether CI identifier is in keywords

    Returns:
        True if should fall through
    """
    if not (plan_intent == Intent.LIST or plan_list_enabled):
        return False
    if not graph_requested:
        return False
    return has_ci_identifier
