"""Next actions utilities for orchestration.

This module handles next action management including insertion, registration,
and finalization. Consolidates duplicate methods that existed in runner.py.
"""

from typing import Any, Dict, List

from app.modules.ops.services.orchestration.actions import NextAction, RerunPayload


class NextActionsHelper:
    """Helper for managing next actions in orchestration.

    Consolidates all next actions related methods from runner.py to
    eliminate duplication and provide unified interface.
    """

    def __init__(self):
        """Initialize next actions helper."""
        self.next_actions: List[NextAction] = []
        self.plan_trace: Dict[str, Any] = {}

    def insert_recommended_actions(self, recommended: List[NextAction]) -> None:
        """Insert recommended actions with priority.

        Recommended actions are prioritized and moved to the front,
        with matching existing actions removed to avoid duplication.

        Args:
            recommended: List of recommended next actions
        """
        prioritized: List[NextAction] = []
        for rec in recommended:
            match = None
            for action in self.next_actions:
                if action.get("label") == rec.get("label"):
                    match = action
                    break
            if match:
                self.next_actions.remove(match)
                prioritized.append(match)
            else:
                prioritized.append(rec)
        self.next_actions = prioritized + self.next_actions

    def register_ambiguous_candidates(
        self, candidates: List[Dict[str, Any]], role: str
    ) -> None:
        """Register ambiguous candidates for rerun.

        When multiple candidates match the user input, store them for
        potential rerun with different selections.

        Args:
            candidates: List of candidate CIs
            role: Role identifier (e.g., "primary", "secondary")
        """
        self.plan_trace["ambiguous"] = True
        roles = self.plan_trace.setdefault("ambiguous_roles", [])
        if role not in roles:
            roles.append(role)
        entries = self.plan_trace.setdefault("candidates", [])
        entries.append({"role": role, "items": candidates})

    def finalize_next_actions(self) -> List[NextAction]:
        """Finalize next actions by adding trace details action.

        Always adds a "Trace details" action at the end for debugging.

        Returns:
            Final list of next actions
        """
        actions = list(self.next_actions)
        actions.append({"type": "open_trace", "label": "Trace details"})
        return actions

    def candidate_next_actions(
        self,
        candidates: List[Dict[str, Any]],
        use_secondary: bool,
        role: str,
    ) -> List[NextAction]:
        """Create next actions from CI candidates.

        Converts candidate CIs into rerun actions that allow user to
        select specific CI for analysis.

        Args:
            candidates: List of candidate CIs
            use_secondary: Whether to use secondary CI selection
            role: Role identifier for UI display

        Returns:
            List of rerun next actions
        """
        actions: List[NextAction] = []
        for candidate in candidates:
            payload: RerunPayload = {}
            if use_secondary:
                payload["selected_secondary_ci_id"] = candidate["ci_id"]
            else:
                payload["selected_ci_id"] = candidate["ci_id"]
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{candidate['ci_code']} 선택 ({role})",
                    "payload": payload,
                }
            )
        return actions
