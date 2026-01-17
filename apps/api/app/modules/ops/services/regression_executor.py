"""
Regression detection service with deterministic judgment rules.

Compares candidate trace against baseline trace and determines if regression occurred.
Uses fixed rules (no LLM) for PASS/WARN/FAIL classification.
"""

from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class RegressionDiffSummary:
    """Summary of differences between baseline and candidate traces"""

    assets_changed: bool
    assets_details: Dict[str, Any]

    plan_intent_changed: bool
    plan_output_changed: bool

    tool_calls_added: int
    tool_calls_removed: int
    tool_calls_failed: int  # count of failed calls in candidate

    blocks_structure_changed: bool  # 50%+ volume change
    blocks_count: Dict[str, Any]  # before, after counts

    references_count_change: Dict[str, Any]  # before, after
    references_variance: float  # percentage change

    tool_duration_spike: bool  # 2x+ duration in any tool

    status_changed: bool  # ok -> error or vice versa
    error_in_candidate: bool

    ui_errors_increase: bool


def compute_regression_diff(
    baseline_trace: Dict[str, Any],
    candidate_trace: Dict[str, Any],
) -> RegressionDiffSummary:
    """
    Compute detailed diff between baseline and candidate traces.

    Returns RegressionDiffSummary object used for judgment rules.
    """

    # 1. Asset version changes
    baseline_assets = baseline_trace.get("asset_versions", [])
    candidate_assets = candidate_trace.get("asset_versions", [])
    assets_changed = baseline_assets != candidate_assets

    # 2. Plan changes
    baseline_plan = baseline_trace.get("plan_validated", {})
    candidate_plan = candidate_trace.get("plan_validated", {})

    plan_intent_changed = (
        baseline_plan.get("intent") != candidate_plan.get("intent")
    )
    plan_output_changed = (
        baseline_plan.get("output") != candidate_plan.get("output")
    )

    # 3. Tool call changes - match by signature
    baseline_steps = baseline_trace.get("execution_steps", [])
    candidate_steps = candidate_trace.get("execution_steps", [])

    (
        tool_added_count,
        tool_removed_count,
        tool_failed_count,
        tool_duration_spike,
    ) = _analyze_tool_calls(baseline_steps, candidate_steps)

    # 4. Answer blocks structure
    baseline_blocks = baseline_trace.get("answer", {}).get("blocks", [])
    candidate_blocks = candidate_trace.get("answer", {}).get("blocks", [])

    blocks_structure_changed = _blocks_structure_changed(
        baseline_blocks, candidate_blocks
    )

    baseline_block_count = len(baseline_blocks)
    candidate_block_count = len(candidate_blocks)

    # 5. References count variance
    baseline_refs = baseline_trace.get("references", [])
    candidate_refs = candidate_trace.get("references", [])

    baseline_ref_count = len(baseline_refs)
    candidate_ref_count = len(candidate_refs)

    ref_variance = (
        0.0
        if baseline_ref_count == 0
        else abs(candidate_ref_count - baseline_ref_count)
        / baseline_ref_count
    )

    # 6. Status changes
    baseline_status = baseline_trace.get("status", "unknown")
    candidate_status = candidate_trace.get("status", "unknown")
    status_changed = baseline_status != candidate_status
    error_in_candidate = candidate_status == "error"

    # 7. UI render errors
    baseline_ui = baseline_trace.get("ui_render", {})
    candidate_ui = candidate_trace.get("ui_render", {})

    baseline_ui_errors = baseline_ui.get("error_count", 0)
    candidate_ui_errors = candidate_ui.get("error_count", 0)
    ui_errors_increase = candidate_ui_errors > baseline_ui_errors

    return RegressionDiffSummary(
        assets_changed=assets_changed,
        assets_details={
            "baseline": baseline_assets,
            "candidate": candidate_assets,
        },
        plan_intent_changed=plan_intent_changed,
        plan_output_changed=plan_output_changed,
        tool_calls_added=tool_added_count,
        tool_calls_removed=tool_removed_count,
        tool_calls_failed=tool_failed_count,
        blocks_structure_changed=blocks_structure_changed,
        blocks_count={
            "before": baseline_block_count,
            "after": candidate_block_count,
        },
        references_count_change={
            "before": baseline_ref_count,
            "after": candidate_ref_count,
        },
        references_variance=ref_variance,
        tool_duration_spike=tool_duration_spike,
        status_changed=status_changed,
        error_in_candidate=error_in_candidate,
        ui_errors_increase=ui_errors_increase,
    )


def determine_judgment(diff: RegressionDiffSummary) -> tuple[str, str]:
    """
    Deterministic judgment rules for regression detection.

    Returns: (judgment: "PASS"|"WARN"|"FAIL", reason: str)

    Rules:
    ------
    FAIL conditions (any match = FAIL):
    - Status changed (ok -> error or error -> ok)
    - Tool calls added/removed/failed (tool additions/deletions/errors)
    - Asset version changes
    - Plan intent or output changes
    - Block structure changes (50%+ volume variance)
    - Tool call error in candidate
    - UI errors increased

    WARN conditions (no FAIL, any match = WARN):
    - References count variance > 20%
    - Tool duration spike (2x+)

    PASS:
    - No FAIL or WARN conditions met
    """

    # FAIL conditions
    if diff.status_changed:
        return "FAIL", f"Status changed: {diff.status_changed}"

    if diff.error_in_candidate:
        return "FAIL", "Candidate execution resulted in error"

    if diff.tool_calls_added > 0 or diff.tool_calls_removed > 0:
        return (
            "FAIL",
            f"Tool calls changed: +{diff.tool_calls_added} -{diff.tool_calls_removed}",
        )

    if diff.tool_calls_failed > 0:
        return "FAIL", f"Tool calls failed in candidate: {diff.tool_calls_failed}"

    if diff.assets_changed:
        return "FAIL", "Asset versions changed"

    if diff.plan_intent_changed or diff.plan_output_changed:
        return "FAIL", "Plan intent or output changed"

    # Check block structure variance (50%+)
    before = diff.blocks_count["before"]
    after = diff.blocks_count["after"]
    if before > 0:
        block_variance = abs(after - before) / before
        if block_variance >= 0.5:
            return (
                "FAIL",
                f"Block structure changed significantly ({block_variance:.1%})",
            )

    if diff.ui_errors_increase:
        return "FAIL", "UI render errors increased"

    # WARN conditions
    if diff.references_variance > 0.2:  # 20%+ variance
        return (
            "WARN",
            f"Reference count variance: {diff.references_variance:.1%}",
        )

    if diff.tool_duration_spike:
        return "WARN", "Tool execution duration spike (2x+ in some tools)"

    # PASS
    return "PASS", "No regressions detected"


def _analyze_tool_calls(
    baseline_steps: List[Dict[str, Any]],
    candidate_steps: List[Dict[str, Any]],
) -> tuple[int, int, int, bool]:
    """
    Analyze tool call differences.

    Returns: (added_count, removed_count, failed_count, duration_spike)
    """

    # Simple signature matching: (tool_name, request_keys)
    baseline_sigs = {
        _step_signature(step): step for step in baseline_steps
    }
    candidate_sigs = {
        _step_signature(step): step for step in candidate_steps
    }

    added = len(set(candidate_sigs.keys()) - set(baseline_sigs.keys()))
    removed = len(set(baseline_sigs.keys()) - set(candidate_sigs.keys()))

    # Check for failed calls in candidate
    failed = sum(
        1
        for step in candidate_steps
        if step.get("error") and step.get("error").get("message")
    )

    # Check for duration spike (2x+)
    duration_spike = False
    for sig in set(baseline_sigs.keys()) & set(candidate_sigs.keys()):
        baseline_dur = baseline_sigs[sig].get("duration_ms", 0)
        candidate_dur = candidate_sigs[sig].get("duration_ms", 0)
        if baseline_dur > 0 and candidate_dur > baseline_dur * 2:
            duration_spike = True
            break

    return added, removed, failed, duration_spike


def _step_signature(step: Dict[str, Any]) -> tuple:
    """Generate signature for tool call matching"""
    tool_name = step.get("step_id", "").split(":")[0]  # Extract tool name
    request_keys = tuple(
        sorted(step.get("request", {}).keys()) if step.get("request") else ()
    )
    return (tool_name, request_keys)


def _blocks_structure_changed(
    baseline_blocks: List[Dict[str, Any]],
    candidate_blocks: List[Dict[str, Any]],
) -> bool:
    """Check if block structure changed significantly"""

    # Type distribution before and after
    baseline_types = {}
    for block in baseline_blocks:
        block_type = block.get("type", "unknown")
        baseline_types[block_type] = baseline_types.get(block_type, 0) + 1

    candidate_types = {}
    for block in candidate_blocks:
        block_type = block.get("type", "unknown")
        candidate_types[block_type] = candidate_types.get(block_type, 0) + 1

    # Different types present or significant count changes
    if set(baseline_types.keys()) != set(candidate_types.keys()):
        return True

    # Check for block mapping failures (type -> type mapping issues)
    # This would indicate structural problems in result generation
    return False
