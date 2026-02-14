"""
Execution Router Module - Phase 9

Extracts routing decision logic from runner.py including:
- Execution mode routing (direct, lookup, sections, auto_recipe)
- Plan analysis and route decision
- Routing intent detection
- Fallback routing logic
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from core.logging import get_logger

from app.modules.ops.services.orchestration.planner.plan_schema import (
    PlanOutput,
    PlanOutputKind,
    View,
)

MODULE_LOGGER = get_logger(__name__)

ExecutionRoute = Literal[
    "direct",
    "lookup",
    "sections_loop",
    "auto_recipe",
    "error",
]


class ExecutionRouter:
    """
    Routes execution based on plan analysis and context.

    Responsibilities:
    - Determine execution route from plan
    - Analyze plan intent and structure
    - Apply fallback routing logic
    - Make routing decisions based on CI context
    """

    def __init__(self, tenant_id: str, logger: Any = None):
        """
        Initialize ExecutionRouter.

        Args:
            tenant_id: Current tenant ID
            logger: Logger instance
        """
        self.tenant_id = tenant_id
        self.logger = logger or MODULE_LOGGER

    def determine_route(
        self,
        plan_output: PlanOutput,
        has_ci_context: bool = False,
        has_metrics: bool = False,
    ) -> ExecutionRoute:
        """
        Determine execution route based on plan analysis.

        Args:
            plan_output: Plan output from planner
            has_ci_context: Whether CI context is available
            has_metrics: Whether metrics data is available

        Returns:
            Route identifier
        """
        # Route based on plan output kind
        if plan_output.kind == PlanOutputKind.DIRECT:
            return "direct"

        if plan_output.kind == PlanOutputKind.REJECT:
            return "error"

        # Plan output - analyze further
        if not plan_output.plan:
            return "error"

        # Check for sections-based orchestration
        if self._should_use_sections_loop(plan_output):
            return "sections_loop"

        # Check for auto recipe
        if self._should_use_auto_recipe(plan_output):
            return "auto_recipe"

        # Check for lookup
        if self._should_use_lookup(plan_output):
            return "lookup"

        # Default fallback
        return "sections_loop"

    def _should_use_sections_loop(self, plan_output: PlanOutput) -> bool:
        """Check if sections loop execution should be used."""
        if not plan_output.plan:
            return False

        # Check if plan has views/sections defined
        if hasattr(plan_output.plan, "views"):
            return bool(plan_output.plan.views)

        if hasattr(plan_output.plan, "sections"):
            return bool(plan_output.plan.sections)

        return False

    def _should_use_auto_recipe(self, plan_output: PlanOutput) -> bool:
        """Check if auto recipe should be used."""
        if not plan_output.plan:
            return False

        # Check for auto_spec indicating auto recipe
        if hasattr(plan_output.plan, "auto_spec"):
            return plan_output.plan.auto_spec is not None

        return False

    def _should_use_lookup(self, plan_output: PlanOutput) -> bool:
        """Check if lookup-based execution should be used."""
        if not plan_output.plan:
            return False

        # Simple lookup if just looking for CI info
        intent = getattr(plan_output.plan, "intent", None)
        if intent:
            intent_str = intent.value if hasattr(intent, "value") else str(intent)
            lookup_intents = [
                "lookup_ci",
                "get_ci_detail",
                "ci_info",
            ]
            return any(
                lookup_intent in intent_str.lower()
                for lookup_intent in lookup_intents
            )

        return False

    def get_route_config(
        self,
        route: ExecutionRoute,
    ) -> Dict[str, Any]:
        """
        Get configuration for a specific route.

        Args:
            route: Route identifier

        Returns:
            Route configuration dict
        """
        configs = {
            "direct": {
                "description": "Direct answer from planner",
                "stages": ["route", "present"],
                "requires_execution": False,
            },
            "lookup": {
                "description": "Simple CI lookup",
                "stages": ["route", "validate", "execute", "present"],
                "requires_execution": True,
                "execution_type": "lookup",
            },
            "sections_loop": {
                "description": "Section-based orchestration",
                "stages": [
                    "route",
                    "validate",
                    "execute_sections",
                    "compose",
                    "present",
                ],
                "requires_execution": True,
                "execution_type": "sections",
            },
            "auto_recipe": {
                "description": "Automated recipe-based orchestration",
                "stages": ["route", "validate", "execute_recipe", "compose", "present"],
                "requires_execution": True,
                "execution_type": "recipe",
            },
            "error": {
                "description": "Error/rejection route",
                "stages": ["route", "present"],
                "requires_execution": False,
            },
        }

        return configs.get(
            route,
            {
                "description": "Unknown route",
                "stages": ["route"],
                "requires_execution": False,
            },
        )

    def analyze_plan_structure(
        self,
        plan_output: PlanOutput,
    ) -> Dict[str, Any]:
        """
        Analyze plan structure for routing decisions.

        Args:
            plan_output: Plan output from planner

        Returns:
            Structure analysis dict
        """
        analysis = {
            "kind": plan_output.kind.value,
            "has_plan": plan_output.plan is not None,
            "has_views": False,
            "has_sections": False,
            "has_auto_spec": False,
            "intent": None,
            "ci_focus": False,
            "metric_focus": False,
            "graph_focus": False,
        }

        if plan_output.plan:
            analysis["has_views"] = bool(
                getattr(plan_output.plan, "views", None)
            )
            analysis["has_sections"] = bool(
                getattr(plan_output.plan, "sections", None)
            )
            analysis["has_auto_spec"] = (
                getattr(plan_output.plan, "auto_spec", None) is not None
            )
            analysis["intent"] = str(getattr(plan_output.plan, "intent", None))

            # Check for focus areas
            if hasattr(plan_output.plan, "views"):
                views = plan_output.plan.views or []
                view_values = [
                    v.value if hasattr(v, "value") else str(v)
                    for v in views
                ]
                analysis["graph_focus"] = View.COMPOSITION.value in view_values or \
                                         View.DEPENDENCY.value in view_values
                analysis["metric_focus"] = any(
                    "metric" in v.lower() for v in view_values
                )

        return analysis

    def get_routing_context(
        self,
        ci_id: str | None,
        ci_code: str | None,
        has_graph_request: bool = False,
        has_metric_request: bool = False,
    ) -> Dict[str, Any]:
        """
        Get routing context from question parameters.

        Args:
            ci_id: CI ID if provided
            ci_code: CI code if provided
            has_graph_request: Whether graph visualization is requested
            has_metric_request: Whether metrics are requested

        Returns:
            Routing context dict
        """
        return {
            "ci_id": ci_id,
            "ci_code": ci_code,
            "has_ci_context": bool(ci_id or ci_code),
            "has_graph_request": has_graph_request,
            "has_metric_request": has_metric_request,
            "is_specific_lookup": bool(
                ci_id or ci_code
            ),
        }
