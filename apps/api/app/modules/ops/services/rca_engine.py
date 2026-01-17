"""
RCA Assist Engine - Deterministic Root Cause Analysis

Generates hypotheses for failure/regression analysis based on fixed rules.
LLM is used only for text summarization, not for hypothesis generation.
"""

from typing import Any, Dict, List, Literal
from dataclasses import dataclass, field
import json


@dataclass
class EvidencePath:
    """Reference to evidence in a trace"""
    path: str  # e.g., "tool_calls[2].error.message"
    snippet: str  # Extracted value from trace
    display: str = ""  # User-friendly label


@dataclass
class RCAHypothesis:
    """Root cause hypothesis with evidence and actions"""
    rank: int
    title: str
    confidence: Literal["high", "medium", "low"]
    evidence: List[EvidencePath] = field(default_factory=list)
    checks: List[str] = field(default_factory=list)  # Operator verification steps
    recommended_actions: List[str] = field(default_factory=list)
    description: str = ""  # LLM-generated summary


class RCAEngine:
    """Deterministic RCA rule engine for single trace and diff analysis"""

    def __init__(self):
        self.hypotheses: List[RCAHypothesis] = []
        self.rule_matches: Dict[str, Any] = {}

    def analyze_single_trace(
        self,
        trace: Dict[str, Any],
        max_hypotheses: int = 5,
    ) -> List[RCAHypothesis]:
        """
        Analyze a single trace for failure/issue causes.

        Rules checked (in order of priority):
        1. Tool call errors (timeout, auth, 5xx, SQL errors)
        2. Fallback asset usage
        3. Plan steps exceed limits
        4. No data returned (normal case)
        5. Tool duration spike
        6. UI mapping failures
        7. Validator policy violations
        8. Plan intent misclassification
        9. SQL zero-row results
        10. HTTP auth errors
        """
        self.hypotheses = []

        # Extract key trace elements
        status = trace.get("status", "unknown")
        execution_steps = trace.get("execution_steps", [])
        plan_validated = trace.get("plan_validated", {})
        references = trace.get("references", [])
        answer = trace.get("answer", {})
        ui_render = trace.get("ui_render", {})
        applied_assets = trace.get("applied_assets", {})
        fallbacks = trace.get("fallbacks", {})

        # Rule 1: Tool call errors
        if status == "error" and execution_steps:
            self._check_tool_errors(execution_steps)

        # Rule 2: Fallback asset usage
        if fallbacks and any(fallbacks.values()):
            self._check_fallback_assets(applied_assets, fallbacks)

        # Rule 3: Plan step overflow
        steps = plan_validated.get("steps", []) if plan_validated else []
        if steps:
            self._check_plan_step_limits(steps, plan_validated)

        # Rule 4: No data (normal case)
        if not references and "No data" in answer.get("meta", {}).get("summary", ""):
            self._check_no_data_normal(answer)

        # Rule 5: Tool duration spike
        if execution_steps:
            self._check_tool_duration_spike(execution_steps)

        # Rule 6: UI mapping failures
        if ui_render and ui_render.get("error_count", 0) > 0:
            self._check_ui_mapping_failures(ui_render)

        # Rule 7: Validator policy violations
        if plan_validated and plan_validated.get("policy_violations"):
            self._check_validator_violations(plan_validated)

        # Rule 8: Plan intent misclassification
        if plan_validated and plan_validated.get("intent") == "list" and plan_validated.get("view") == "graph":
            self._check_intent_misclassify(plan_validated)

        # Rule 9: SQL zero-row results
        if references:
            for ref in references:
                if ref.get("ref_type", "").startswith("SQL") and ref.get("row_count") == 0:
                    self._check_sql_zero_rows(ref)

        # Rule 10: HTTP auth errors
        if references:
            for ref in references:
                if ref.get("ref_type", "").startswith("HTTP"):
                    self._check_http_auth_errors(ref, execution_steps)

        # Sort by confidence and return top N
        self._rank_hypotheses()
        return self.hypotheses[:max_hypotheses]

    def analyze_diff(
        self,
        baseline_trace: Dict[str, Any],
        candidate_trace: Dict[str, Any],
        max_hypotheses: int = 7,
    ) -> List[RCAHypothesis]:
        """
        Analyze difference between baseline and candidate traces.

        Rules checked:
        1. Asset version changes
        2. Plan changes
        3. Tool call additions/removals
        4. Tool errors introduced
        5. Block structure changes
        6. UI render regression
        7. Reference data reduction
        8. Performance regression
        """
        self.hypotheses = []

        baseline_assets = baseline_trace.get("asset_versions", [])
        candidate_assets = candidate_trace.get("asset_versions", [])
        baseline_plan = baseline_trace.get("plan_validated", {})
        candidate_plan = candidate_trace.get("plan_validated", {})
        baseline_steps = baseline_trace.get("execution_steps", [])
        candidate_steps = candidate_trace.get("execution_steps", [])
        baseline_blocks = baseline_trace.get("answer", {}).get("blocks", [])
        candidate_blocks = candidate_trace.get("answer", {}).get("blocks", [])
        baseline_refs = baseline_trace.get("references") or []
        candidate_refs = candidate_trace.get("references") or []
        baseline_ui_render = baseline_trace.get("ui_render") or {}
        candidate_ui_render = candidate_trace.get("ui_render") or {}
        baseline_ui_errors = baseline_ui_render.get("error_count", 0)
        candidate_ui_errors = candidate_ui_render.get("error_count", 0)

        # Rule 1: Asset version changes (highest priority)
        if baseline_assets != candidate_assets:
            self._check_asset_changes(baseline_assets, candidate_assets, candidate_trace)

        # Rule 2: Plan changes
        if baseline_plan and candidate_plan and \
           (baseline_plan.get("intent") != candidate_plan.get("intent") or \
            baseline_plan.get("output_types") != candidate_plan.get("output_types")):
            self._check_plan_changes(baseline_plan, candidate_plan)

        # Rule 3: Tool call path changes
        baseline_tool_names = {step.get("step_id", "").split(":")[0] for step in (baseline_steps or [])}
        candidate_tool_names = {step.get("step_id", "").split(":")[0] for step in (candidate_steps or [])}
        if baseline_tool_names != candidate_tool_names:
            self._check_tool_path_changes(baseline_tool_names, candidate_tool_names)

        # Rule 4: New tool errors
        baseline_errors = sum(1 for s in (baseline_steps or []) if s.get("error"))
        candidate_errors = sum(1 for s in (candidate_steps or []) if s.get("error"))
        if candidate_errors > baseline_errors:
            self._check_tool_error_regression(candidate_steps, baseline_steps)

        # Rule 5: Block structure changes
        if baseline_blocks and candidate_blocks and \
           (len(baseline_blocks) != len(candidate_blocks) or \
            {b.get("type") for b in baseline_blocks} != {b.get("type") for b in candidate_blocks}):
            self._check_block_structure_change(baseline_blocks, candidate_blocks)

        # Rule 6: UI render regression
        if candidate_ui_errors > baseline_ui_errors:
            self._check_ui_render_regression(baseline_ui_errors, candidate_ui_errors)

        # Rule 7: Data reduction
        baseline_refs = baseline_refs or []
        candidate_refs = candidate_refs or []
        if len(candidate_refs) < len(baseline_refs) * 0.8 and len(baseline_refs) > 0:
            self._check_data_reduction(baseline_refs, candidate_refs)

        # Rule 8: Performance regression
        baseline_duration = baseline_trace.get("duration_ms", 0)
        candidate_duration = candidate_trace.get("duration_ms", 0)
        if candidate_duration > baseline_duration * 2:
            self._check_performance_regression(baseline_duration, candidate_duration)

        # Sort by confidence and return top N
        self._rank_hypotheses()
        return self.hypotheses[:max_hypotheses]

    # ===== Single Trace Rules =====

    def _check_tool_errors(self, execution_steps: List[Dict]):
        """Rule 1: Analyze tool errors by type"""
        for i, step in enumerate(execution_steps):
            if not step.get("error"):
                continue

            error = step.get("error", {})
            error_msg = error.get("message", "").lower()
            error_type = error.get("type", "")
            tool_name = step.get("step_id", "").split(":")[0]

            # Timeout detection
            if "timeout" in error_msg or "timed out" in error_msg:
                self.hypotheses.append(RCAHypothesis(
                    rank=1,
                    title=f"Tool timeout: {tool_name}",
                    confidence="high",
                    evidence=[
                        EvidencePath(
                            path=f"execution_steps[{i}].error.message",
                            snippet=error_msg[:100],
                            display="Error message mentions timeout"
                        )
                    ],
                    checks=[
                        f"Check timeout policy for {tool_name} in published policy asset",
                        "Verify network/service response time in staging",
                        f"Increase timeout threshold and re-run"
                    ],
                    recommended_actions=[
                        f"Adjust policy timeout for {tool_name}",
                        "Add retry with exponential backoff for transient timeouts",
                        "Consider async execution for slow operations"
                    ]
                ))

            # Auth error detection
            elif "401" in error_msg or "403" in error_msg or "auth" in error_msg.lower() or "unauthorized" in error_msg.lower():
                self.hypotheses.append(RCAHypothesis(
                    rank=1,
                    title=f"Authentication/authorization failure: {tool_name}",
                    confidence="high",
                    evidence=[
                        EvidencePath(
                            path=f"execution_steps[{i}].error.message",
                            snippet=error_msg[:100],
                            display="Auth/permission error"
                        )
                    ],
                    checks=[
                        f"Verify API credentials/tokens for {tool_name}",
                        "Check token expiration and refresh policy",
                        "Confirm service account permissions in target system"
                    ],
                    recommended_actions=[
                        "Rotate/refresh API credentials",
                        "Update policy with correct authentication method",
                        "Add token expiration detection and refresh logic"
                    ]
                ))

            # HTTP 5xx error
            elif any(code in error_msg for code in ["500", "502", "503", "504", "5xx"]):
                self.hypotheses.append(RCAHypothesis(
                    rank=1,
                    title=f"External service error (5xx): {tool_name}",
                    confidence="high",
                    evidence=[
                        EvidencePath(
                            path=f"execution_steps[{i}].error.message",
                            snippet=error_msg[:100],
                            display="HTTP 5xx server error"
                        )
                    ],
                    checks=[
                        f"Check {tool_name} service status page",
                        "Verify service is accessible and healthy",
                        "Check request payload for issues"
                    ],
                    recommended_actions=[
                        f"Monitor {tool_name} availability",
                        "Implement circuit breaker pattern",
                        "Add fallback data source if available"
                    ]
                ))

            # SQL error
            elif "sql" in error_msg.lower() or error_type.lower() == "sqlerror":
                self.hypotheses.append(RCAHypothesis(
                    rank=1,
                    title=f"SQL execution error: {tool_name}",
                    confidence="high",
                    evidence=[
                        EvidencePath(
                            path=f"execution_steps[{i}].error.message",
                            snippet=error_msg[:100],
                            display="SQL error detected"
                        )
                    ],
                    checks=[
                        "Verify SQL syntax in generated query",
                        "Check schema and table names are correct",
                        "Confirm user permissions in database",
                        "Test query manually in SQL client"
                    ],
                    recommended_actions=[
                        "Fix SQL query generation logic",
                        "Add query validation before execution",
                        "Improve error handling for schema changes"
                    ]
                ))

    def _check_fallback_assets(self, applied_assets: Dict, fallbacks: Dict):
        """Rule 2: Detect fallback asset usage"""
        fallback_list = [k for k, v in fallbacks.items() if v]
        for asset_key in fallback_list:
            asset_info = applied_assets.get(asset_key, {})
            self.hypotheses.append(RCAHypothesis(
                rank=2,
                title=f"Fallback asset used: {asset_key}",
                confidence="medium",
                evidence=[
                    EvidencePath(
                        path=f"fallbacks.{asset_key}",
                        snippet="true",
                        display=f"Fallback used for {asset_key}"
                    )
                ],
                checks=[
                    f"Verify {asset_key} is published in asset registry",
                    f"Check if {asset_key} version is correct",
                    f"Confirm fallback policy allows {asset_key}"
                ],
                recommended_actions=[
                    f"Publish missing {asset_key} asset",
                    "Update policy to reference correct asset version",
                    f"Remove {asset_key} from fallback list"
                ]
            ))

    def _check_plan_step_limits(self, steps: List, plan_validated: Dict):
        """Rule 3: Detect step limit violations"""
        step_count = len(steps)
        max_steps = plan_validated.get("config", {}).get("max_steps", 50)
        if step_count >= max_steps * 0.9:
            self.hypotheses.append(RCAHypothesis(
                rank=3,
                title=f"Plan complexity near limit ({step_count}/{max_steps} steps)",
                confidence="medium",
                evidence=[
                    EvidencePath(
                        path="plan_validated.steps.length",
                        snippet=str(step_count),
                        display=f"{step_count} steps in plan"
                    ),
                    EvidencePath(
                        path="plan_validated.config.max_steps",
                        snippet=str(max_steps),
                        display=f"Policy limit: {max_steps} steps"
                    )
                ],
                checks=[
                    "Review plan steps for redundancy",
                    "Consolidate multiple steps into single operations",
                    "Verify step ordering is optimal"
                ],
                recommended_actions=[
                    "Optimize planner to generate fewer steps",
                    "Consider splitting complex questions",
                    "Increase policy step limit if justified"
                ]
            ))

    def _check_no_data_normal(self, answer: Dict):
        """Rule 4: Detect 'no data' as normal (low priority)"""
        self.hypotheses.append(RCAHypothesis(
            rank=10,  # Lowest priority
            title="No data returned (likely normal)",
            confidence="low",
            evidence=[
                EvidencePath(
                    path="answer.meta.summary",
                    snippet="No data found",
                    display="Empty result is likely correct"
                )
            ],
            checks=[
                "Verify search criteria in query",
                "Confirm query filters are appropriate",
                "Check if data should exist in source system"
            ],
            recommended_actions=[
                "Adjust query filters if needed",
                "Document that empty results are expected for this query"
            ]
        ))

    def _check_tool_duration_spike(self, execution_steps: List[Dict]):
        """Rule 5: Detect tool duration spikes"""
        durations = [(i, step.get("step_id", ""), step.get("duration_ms", 0))
                     for i, step in enumerate(execution_steps)]
        avg_duration = sum(d[2] for d in durations) / len(durations) if durations else 0

        for i, tool_name, duration in durations:
            if duration > avg_duration * 3 and duration > 1000:
                self.hypotheses.append(RCAHypothesis(
                    rank=4,
                    title=f"Tool performance issue: {tool_name} ({duration}ms)",
                    confidence="medium",
                    evidence=[
                        EvidencePath(
                            path=f"execution_steps[{i}].duration_ms",
                            snippet=str(duration),
                            display=f"Took {duration}ms (avg: {int(avg_duration)}ms)"
                        )
                    ],
                    checks=[
                        f"Profile {tool_name} execution in staging",
                        "Check database query plan for {tool_name}",
                        f"Verify {tool_name} external service latency"
                    ],
                    recommended_actions=[
                        f"Optimize {tool_name} query/request",
                        "Add indexing or caching if applicable",
                        f"Consider timeout policy change for {tool_name}"
                    ]
                ))

    def _check_ui_mapping_failures(self, ui_render: Dict):
        """Rule 6: Detect UI component mapping issues"""
        error_count = ui_render.get("error_count", 0)
        total_components = ui_render.get("rendered_count", 0)
        error_details = ui_render.get("errors", [])

        error_msg = str(error_details[0]) if error_details else "UI mapping failed"

        self.hypotheses.append(RCAHypothesis(
            rank=5,
            title=f"UI component rendering issues ({error_count} errors)",
            confidence="medium",
            evidence=[
                EvidencePath(
                    path="ui_render.error_count",
                    snippet=str(error_count),
                    display=f"{error_count} UI component mapping errors"
                ),
                EvidencePath(
                    path="ui_render.errors[0]",
                    snippet=error_msg[:80],
                    display="Error detail"
                )
            ],
            checks=[
                "Review answer blocks for unsupported types",
                "Check UI component mapping configuration",
                "Verify block schema matches renderer expectations"
            ],
            recommended_actions=[
                "Update answer block types to match renderer",
                "Add missing UI component mappers",
                "Improve error recovery for unsupported blocks"
            ]
        ))

    def _check_validator_violations(self, plan_validated: Dict):
        """Rule 7: Detect validator policy violations"""
        violations = plan_validated.get("policy_violations", [])
        for violation in violations:
            self.hypotheses.append(RCAHypothesis(
                rank=2,
                title=f"Validator policy violation: {violation.get('rule', 'unknown')}",
                confidence="high",
                evidence=[
                    EvidencePath(
                        path="plan_validated.policy_violations[*].rule",
                        snippet=violation.get("rule", ""),
                        display=f"Policy rule: {violation.get('rule', '')}"
                    )
                ],
                checks=[
                    f"Review policy rule: {violation.get('rule', '')}",
                    "Verify plan configuration complies with policy",
                    "Check if policy should be relaxed or plan adjusted"
                ],
                recommended_actions=[
                    "Adjust plan to comply with policy",
                    "Update policy if current constraint is too strict",
                    "Add explicit policy exception if justified"
                ]
            ))

    def _check_intent_misclassify(self, plan_validated: Dict):
        """Rule 8: Detect planner intent misclassification"""
        self.hypotheses.append(RCAHypothesis(
            rank=6,
            title="Planner intent misclassification (list vs graph)",
            confidence="medium",
            evidence=[
                EvidencePath(
                    path="plan_validated.intent",
                    snippet=plan_validated.get("intent", ""),
                    display="Intent set to list but view is graph"
                )
            ],
            checks=[
                "Review planner intent classification prompt",
                "Verify question is truly list vs graph",
                "Check if intent keywords are being recognized"
            ],
            recommended_actions=[
                "Improve intent classification prompt",
                "Add explicit keywords detection",
                "Consider semantic similarity check"
            ]
        ))

    def _check_sql_zero_rows(self, reference: Dict):
        """Rule 9: Detect SQL queries returning zero rows"""
        self.hypotheses.append(RCAHypothesis(
            rank=7,
            title=f"SQL query returned 0 rows: {reference.get('name', 'unknown')}",
            confidence="low",
            evidence=[
                EvidencePath(
                    path=f"references[*].row_count",
                    snippet="0",
                    display="Query returned no rows"
                )
            ],
            checks=[
                f"Verify query filters: {reference.get('statement', '')[:80]}",
                "Check if filtering conditions are too restrictive",
                "Confirm data exists in source with those criteria"
            ],
            recommended_actions=[
                "Relax filter conditions",
                "Check date range or time filters",
                "Verify identifier values (IDs, names, etc.)"
            ]
        ))

    def _check_http_auth_errors(self, reference: Dict, execution_steps: List[Dict]):
        """Rule 10: Detect HTTP auth errors"""
        for step in execution_steps:
            if reference.get("name") in step.get("step_id", ""):
                error = step.get("error", {})
                if error and ("401" in str(error) or "403" in str(error)):
                    self.hypotheses.append(RCAHypothesis(
                        rank=1,
                        title=f"HTTP auth error: {reference.get('name', 'unknown')}",
                        confidence="high",
                        evidence=[
                            EvidencePath(
                                path=f"references[*].name",
                                snippet=reference.get("name", ""),
                                display="HTTP endpoint with auth failure"
                            )
                        ],
                        checks=[
                            f"Verify credentials for {reference.get('name', '')}",
                            "Check token expiration",
                            "Confirm API key is active"
                        ],
                        recommended_actions=[
                            "Refresh API credentials",
                            "Update auth configuration",
                            "Add credential validation before execution"
                        ]
                    ))

    # ===== Diff Trace Rules =====

    def _check_asset_changes(self, baseline_assets: List[str], candidate_assets: List[str], candidate_trace: Dict):
        """Rule 1 (Diff): Asset version changes (highest priority)"""
        changed_assets = set(baseline_assets).symmetric_difference(set(candidate_assets))
        for asset in changed_assets:
            self.hypotheses.append(RCAHypothesis(
                rank=1,
                title=f"Asset version changed: {asset}",
                confidence="high",
                evidence=[
                    EvidencePath(
                        path="asset_versions",
                        snippet=f"{asset}",
                        display="Asset version in candidate differs from baseline"
                    )
                ],
                checks=[
                    f"Review changelog for {asset}",
                    "Verify new asset version behavior",
                    "Test asset in isolation in staging"
                ],
                recommended_actions=[
                    f"Validate new {asset} version",
                    "Revert to previous version if needed",
                    "Add regression tests for {asset}"
                ]
            ))

    def _check_plan_changes(self, baseline_plan: Dict, candidate_plan: Dict):
        """Rule 2 (Diff): Plan changes"""
        changes = []
        if baseline_plan.get("intent") != candidate_plan.get("intent"):
            changes.append(f"intent ({baseline_plan.get('intent')} → {candidate_plan.get('intent')})")
        if baseline_plan.get("output_types") != candidate_plan.get("output_types"):
            changes.append("output_types")

        for change in changes:
            self.hypotheses.append(RCAHypothesis(
                rank=2,
                title=f"Plan changed: {change}",
                confidence="medium",
                evidence=[
                    EvidencePath(
                        path="plan_validated",
                        snippet=change,
                        display="Plan structure differs in candidate"
                    )
                ],
                checks=[
                    "Compare baseline and candidate plans",
                    "Verify plan change is expected",
                    "Test new plan against question intent"
                ],
                recommended_actions=[
                    "Update plan if change is intentional",
                    "Revert plan if regression",
                    "Add explicit plan validation"
                ]
            ))

    def _check_tool_path_changes(self, baseline_tools: set, candidate_tools: set):
        """Rule 3 (Diff): Tool call path changes"""
        added = candidate_tools - baseline_tools
        removed = baseline_tools - candidate_tools

        for tool in added:
            self.hypotheses.append(RCAHypothesis(
                rank=3,
                title=f"Tool call added: {tool}",
                confidence="medium",
                evidence=[
                    EvidencePath(
                        path="execution_steps",
                        snippet=tool,
                        display="New tool call in candidate"
                    )
                ],
                checks=[
                    f"Verify {tool} is necessary",
                    f"Check {tool} output is used",
                    f"Confirm {tool} is functioning"
                ],
                recommended_actions=[
                    f"Review why {tool} was added",
                    f"Optimize or remove if unnecessary",
                    f"Document {tool} usage"
                ]
            ))

        for tool in removed:
            self.hypotheses.append(RCAHypothesis(
                rank=3,
                title=f"Tool call removed: {tool}",
                confidence="medium",
                evidence=[
                    EvidencePath(
                        path="execution_steps",
                        snippet=tool,
                        display="Tool missing in candidate"
                    )
                ],
                checks=[
                    f"Verify {tool} removal doesn't affect result",
                    f"Check if result quality degraded",
                    f"Confirm intent still satisfied"
                ],
                recommended_actions=[
                    f"Restore {tool} if needed",
                    "Verify result completeness",
                    f"Document why {tool} was removed"
                ]
            ))

    def _check_tool_error_regression(self, candidate_steps: List[Dict], baseline_steps: List[Dict]):
        """Rule 4 (Diff): Tool errors introduced in candidate"""
        for i, step in enumerate(candidate_steps):
            if step.get("error"):
                error_msg = step.get("error", {}).get("message", "")
                tool_name = step.get("step_id", "").split(":")[0]
                self.hypotheses.append(RCAHypothesis(
                    rank=2,
                    title=f"Tool error introduced: {tool_name}",
                    confidence="high",
                    evidence=[
                        EvidencePath(
                            path=f"execution_steps[{i}].error.message",
                            snippet=error_msg[:80],
                            display="New error in candidate"
                        )
                    ],
                    checks=[
                        f"Verify {tool_name} is available",
                        "Check tool configuration",
                        "Confirm service is healthy"
                    ],
                    recommended_actions=[
                        f"Fix {tool_name} issue",
                        "Restore to baseline version",
                        f"Add error handling for {tool_name}"
                    ]
                ))

    def _check_block_structure_change(self, baseline_blocks: List[Dict], candidate_blocks: List[Dict]):
        """Rule 5 (Diff): Block structure changes"""
        baseline_types = {b.get("type") for b in baseline_blocks}
        candidate_types = {b.get("type") for b in candidate_blocks}

        if baseline_types != candidate_types:
            added_types = candidate_types - baseline_types
            removed_types = baseline_types - candidate_types

            for btype in added_types:
                self.hypotheses.append(RCAHypothesis(
                    rank=4,
                    title=f"Answer block type added: {btype}",
                    confidence="medium",
                    evidence=[
                        EvidencePath(
                            path="answer.blocks[*].type",
                            snippet=btype,
                            display=f"New {btype} block in response"
                        )
                    ],
                    checks=[
                        f"Verify {btype} block is correct",
                        f"Check {btype} is rendered properly",
                        "Confirm content is accurate"
                    ],
                    recommended_actions=[
                        f"Review {btype} output quality",
                        "Update UI if needed",
                        f"Add {btype} validation"
                    ]
                ))

            for btype in removed_types:
                self.hypotheses.append(RCAHypothesis(
                    rank=4,
                    title=f"Answer block type removed: {btype}",
                    confidence="medium",
                    evidence=[
                        EvidencePath(
                            path="answer.blocks[*].type",
                            snippet=btype,
                            display=f"{btype} block missing in response"
                        )
                    ],
                    checks=[
                        f"Verify {btype} removal is correct",
                        "Check result completeness",
                        "Confirm user expectation met"
                    ],
                    recommended_actions=[
                        f"Restore {btype} if needed",
                        "Review output format",
                        f"Document {btype} removal reason"
                    ]
                ))

    def _check_ui_render_regression(self, baseline_errors: int, candidate_errors: int):
        """Rule 6 (Diff): UI render errors increase"""
        self.hypotheses.append(RCAHypothesis(
            rank=5,
            title=f"UI rendering errors increased ({baseline_errors} → {candidate_errors})",
            confidence="medium",
            evidence=[
                EvidencePath(
                    path="ui_render.error_count",
                    snippet=f"{candidate_errors}",
                    display=f"More errors in rendering"
                )
            ],
            checks=[
                "Review new UI error types",
                "Check block schema compliance",
                "Verify component availability"
            ],
            recommended_actions=[
                "Fix block format issues",
                "Update component mappers",
                "Add block validation"
            ]
        ))

    def _check_data_reduction(self, baseline_refs: List[Dict], candidate_refs: List[Dict]):
        """Rule 7 (Diff): Data reduction"""
        baseline_total = sum(r.get("row_count", 0) for r in baseline_refs)
        candidate_total = sum(r.get("row_count", 0) for r in candidate_refs)
        reduction_pct = ((baseline_total - candidate_total) / baseline_total * 100) if baseline_total > 0 else 0

        self.hypotheses.append(RCAHypothesis(
            rank=6,
            title=f"Data reduction detected ({reduction_pct:.0f}% fewer rows)",
            confidence="medium",
            evidence=[
                EvidencePath(
                    path="references[*].row_count",
                    snippet=f"{candidate_total}",
                    display=f"Baseline: {baseline_total} rows → Candidate: {candidate_total} rows"
                )
            ],
            checks=[
                "Review query filters",
                "Check date/time range changes",
                "Verify result completeness"
            ],
            recommended_actions=[
                "Adjust filters if needed",
                "Verify expected data volume",
                "Add data volume validation"
            ]
        ))

    def _check_performance_regression(self, baseline_duration: int, candidate_duration: int):
        """Rule 8 (Diff): Performance regression"""
        slowdown_pct = ((candidate_duration - baseline_duration) / baseline_duration * 100)

        self.hypotheses.append(RCAHypothesis(
            rank=7,
            title=f"Performance regression ({slowdown_pct:.0f}% slower)",
            confidence="medium",
            evidence=[
                EvidencePath(
                    path="duration_ms",
                    snippet=f"{candidate_duration}",
                    display=f"Baseline: {baseline_duration}ms → Candidate: {candidate_duration}ms"
                )
            ],
            checks=[
                "Profile execution to find bottleneck",
                "Check database query plans",
                "Verify external service latency"
            ],
            recommended_actions=[
                "Optimize slow query/tool",
                "Add indexing or caching",
                "Consider timeout adjustment"
            ]
        ))

    # ===== Ranking & Finalization =====

    def _rank_hypotheses(self):
        """Sort hypotheses by confidence and rank"""
        confidence_order = {"high": 0, "medium": 1, "low": 2}

        self.hypotheses.sort(key=lambda h: (
            confidence_order.get(h.confidence, 3),
            h.rank
        ))

        # Reassign ranks based on sorted order
        for i, hyp in enumerate(self.hypotheses, 1):
            hyp.rank = i

    def to_dict(self) -> Dict[str, Any]:
        """Convert hypotheses to JSON-serializable format"""
        return {
            "hypotheses": [
                {
                    "rank": h.rank,
                    "title": h.title,
                    "confidence": h.confidence,
                    "description": h.description,
                    "evidence": [
                        {
                            "path": e.path,
                            "snippet": e.snippet,
                            "display": e.display
                        }
                        for e in h.evidence
                    ],
                    "checks": h.checks,
                    "recommended_actions": h.recommended_actions
                }
                for h in self.hypotheses
            ]
        }
