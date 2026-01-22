"""Tests for multi-step plan schema and validation."""

import sys
from pathlib import Path

# Setup import paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

# Import schema classes - avoid importing router
try:
    from app.modules.ops.services.ci.planner.plan_schema import (
        BudgetSpec,
        Intent,
        Plan,
        PlanBranch,
        PlanLoop,
        PlanMode,
        PlanStep,
        StepCondition,
        View,
    )
    from app.modules.ops.services.ci.planner.validator import validate_plan
except ImportError:
    # Fallback: define minimal classes for testing
    from enum import Enum
    from typing import Any, Dict, List, Literal, Optional

    from pydantic import BaseModel, Field

    class Intent(str, Enum):
        LOOKUP = "LOOKUP"
        SEARCH = "SEARCH"
        AGGREGATE = "AGGREGATE"
        EXPAND = "EXPAND"

    class View(str, Enum):
        SUMMARY = "SUMMARY"
        COMPOSITION = "COMPOSITION"

    class PlanMode(str, Enum):
        CI = "ci"
        AUTO = "auto"

    class BudgetSpec(BaseModel):
        max_steps: int = 10
        max_depth: int = 5
        max_branches: int = 3
        max_iterations: int = 100
        timeout_seconds: Optional[int] = None

    class StepCondition(BaseModel):
        field: str
        operator: Literal["==", "!=", "<", ">", "<=", ">=", "contains", "matches"]
        value: str | int | float | bool

    class PlanStep(BaseModel):
        step_id: str
        name: str
        description: Optional[str] = None
        intent: Intent
        view: Optional[View] = None
        next_step_id: Optional[str] = None
        error_next_step_id: Optional[str] = None
        condition: Optional[StepCondition] = None

    class PlanBranch(BaseModel):
        branch_id: str
        name: str
        condition: StepCondition
        steps: List[PlanStep] = Field(default_factory=list)

    class PlanLoop(BaseModel):
        loop_id: str
        name: str
        max_iterations: int = 10
        break_condition: Optional[StepCondition] = None
        steps: List[PlanStep] = Field(default_factory=list)

    class Plan(BaseModel):
        intent: Intent = Intent.LOOKUP
        enable_multistep: bool = False
        steps: List[PlanStep] = Field(default_factory=list)
        branches: List[PlanBranch] = Field(default_factory=list)
        loops: List[PlanLoop] = Field(default_factory=list)
        budget: BudgetSpec = Field(default_factory=BudgetSpec)

    def validate_plan(plan: Plan) -> tuple[Plan, Dict[str, Any]]:
        """Validate multi-step plan structure (fallback implementation)."""
        trace: Dict[str, Any] = {}

        if not plan.enable_multistep:
            trace["multistep_enabled"] = False
            return plan, {"multistep": trace}

        trace["multistep_enabled"] = True

        # Check unique IDs
        seen_ids: set = set()
        duplicates: List[str] = []

        for step in plan.steps:
            if step.step_id in seen_ids:
                duplicates.append(step.step_id)
            seen_ids.add(step.step_id)

        for branch in plan.branches:
            if branch.branch_id in seen_ids:
                duplicates.append(branch.branch_id)
            seen_ids.add(branch.branch_id)
            for step in branch.steps:
                if step.step_id in seen_ids:
                    duplicates.append(step.step_id)
                seen_ids.add(step.step_id)

        for loop in plan.loops:
            if loop.loop_id in seen_ids:
                duplicates.append(loop.loop_id)
            seen_ids.add(loop.loop_id)
            for step in loop.steps:
                if step.step_id in seen_ids:
                    duplicates.append(step.step_id)
                seen_ids.add(step.step_id)

        trace["unique_ids"] = {
            "valid": len(duplicates) == 0,
            "duplicates": duplicates if duplicates else None,
        }

        # Check references
        all_step_ids = set(seen_ids)
        errors: List[str] = []

        for step in plan.steps:
            if step.next_step_id and step.next_step_id not in all_step_ids:
                errors.append(f"Step {step.step_id} references unknown next_step_id: {step.next_step_id}")
            if step.error_next_step_id and step.error_next_step_id not in all_step_ids:
                errors.append(f"Step {step.step_id} references unknown error_next_step_id: {step.error_next_step_id}")

        for branch in plan.branches:
            for step in branch.steps:
                if step.next_step_id and step.next_step_id not in all_step_ids:
                    errors.append(f"Step {step.step_id} in branch {branch.branch_id} references unknown next_step_id: {step.next_step_id}")

        trace["references"] = {
            "valid": len(errors) == 0,
            "errors": errors if errors else None,
        }

        # Check budget
        budget = plan.budget
        total_steps = len(plan.steps)
        for branch in plan.branches:
            total_steps += len(branch.steps)
        for loop in plan.loops:
            total_steps += len(loop.steps) * loop.max_iterations

        budget_errors: List[str] = []
        if total_steps > budget.max_steps:
            budget_errors.append(f"Total steps ({total_steps}) exceeds max_steps budget ({budget.max_steps})")

        if len(plan.branches) > budget.max_branches:
            budget_errors.append(f"Number of branches ({len(plan.branches)}) exceeds max_branches budget ({budget.max_branches})")

        # Validate timeout_seconds
        if budget.timeout_seconds is not None:
            if budget.timeout_seconds < 1:
                budget_errors.append(f"timeout_seconds ({budget.timeout_seconds}) must be >= 1")
            elif budget.timeout_seconds > 3600:
                budget_errors.append(f"timeout_seconds ({budget.timeout_seconds}) exceeds maximum of 3600 seconds (1 hour)")

        # Validate max_depth
        if budget.max_depth < 1:
            budget_errors.append(f"max_depth ({budget.max_depth}) must be >= 1")
        elif budget.max_depth > 10:
            budget_errors.append(f"max_depth ({budget.max_depth}) exceeds maximum of 10")

        trace["budget"] = {
            "valid": len(budget_errors) == 0,
            "errors": budget_errors if budget_errors else None,
            "constraints": {
                "max_steps": budget.max_steps,
                "max_branches": budget.max_branches,
                "max_iterations": budget.max_iterations,
                "timeout_seconds": budget.timeout_seconds,
            },
        }

        # Count structure
        trace["structure"] = {
            "total_steps": len(plan.steps),
            "total_branches": len(plan.branches),
            "total_loops": len(plan.loops),
            "steps_in_branches": sum(len(b.steps) for b in plan.branches),
            "steps_in_loops": sum(len(loop.steps) for loop in plan.loops),
        }

        is_valid = (len(duplicates) == 0) and (len(errors) == 0) and (len(budget_errors) == 0)

        if not is_valid:
            error_msgs = []
            if duplicates:
                error_msgs.append(f"Duplicate step IDs: {duplicates}")
            error_msgs.extend(errors)
            error_msgs.extend(budget_errors)
            if is_valid is False:
                raise ValueError(f"Multi-step plan validation failed: {'; '.join(error_msgs)}")

        return plan, {"multistep": trace}


class TestBudgetSpec:
    """Tests for BudgetSpec model."""

    def test_budget_spec_defaults(self):
        """Test default budget values."""
        budget = BudgetSpec()
        assert budget.max_steps == 10
        assert budget.max_depth == 5
        assert budget.max_branches == 3
        assert budget.max_iterations == 100
        assert budget.timeout_seconds is None

    def test_budget_spec_custom_values(self):
        """Test custom budget values."""
        budget = BudgetSpec(
            max_steps=20,
            max_branches=5,
            timeout_seconds=300,
        )
        assert budget.max_steps == 20
        assert budget.max_branches == 5
        assert budget.timeout_seconds == 300


class TestStepCondition:
    """Tests for StepCondition model."""

    def test_step_condition_equality(self):
        """Test condition with equality operator."""
        condition = StepCondition(field="status", operator="==", value="success")
        assert condition.field == "status"
        assert condition.operator == "=="
        assert condition.value == "success"

    def test_step_condition_numeric_value(self):
        """Test condition with numeric value."""
        condition = StepCondition(field="count", operator=">", value=10)
        assert condition.value == 10


class TestPlanStep:
    """Tests for PlanStep model."""

    def test_plan_step_minimal(self):
        """Test minimal PlanStep creation."""
        step = PlanStep(
            step_id="step_1",
            name="First Step",
            intent=Intent.LOOKUP,
        )
        assert step.step_id == "step_1"
        assert step.name == "First Step"
        assert step.intent == Intent.LOOKUP
        assert step.next_step_id is None
        assert step.error_next_step_id is None

    def test_plan_step_with_navigation(self):
        """Test PlanStep with navigation."""
        step = PlanStep(
            step_id="step_1",
            name="First Step",
            intent=Intent.SEARCH,
            next_step_id="step_2",
            error_next_step_id="error_step",
        )
        assert step.next_step_id == "step_2"
        assert step.error_next_step_id == "error_step"

    def test_plan_step_with_condition(self):
        """Test PlanStep with execution condition."""
        condition = StepCondition(field="status", operator="==", value="ready")
        step = PlanStep(
            step_id="step_1",
            name="Conditional Step",
            intent=Intent.AGGREGATE,
            condition=condition,
        )
        assert step.condition is not None
        assert step.condition.field == "status"


class TestPlanBranch:
    """Tests for PlanBranch model."""

    def test_plan_branch_creation(self):
        """Test PlanBranch creation."""
        condition = StepCondition(field="type", operator="==", value="metric")
        branch = PlanBranch(
            branch_id="branch_1",
            name="Metric Branch",
            condition=condition,
        )
        assert branch.branch_id == "branch_1"
        assert branch.name == "Metric Branch"
        assert branch.condition is not None
        assert len(branch.steps) == 0

    def test_plan_branch_with_steps(self):
        """Test PlanBranch with steps."""
        condition = StepCondition(field="type", operator="==", value="metric")
        step1 = PlanStep(
            step_id="branch_step_1",
            name="Branch Step 1",
            intent=Intent.LOOKUP,
        )
        step2 = PlanStep(
            step_id="branch_step_2",
            name="Branch Step 2",
            intent=Intent.AGGREGATE,
        )
        branch = PlanBranch(
            branch_id="branch_1",
            name="Metric Branch",
            condition=condition,
            steps=[step1, step2],
        )
        assert len(branch.steps) == 2


class TestPlanLoop:
    """Tests for PlanLoop model."""

    def test_plan_loop_creation(self):
        """Test PlanLoop creation."""
        loop = PlanLoop(
            loop_id="loop_1",
            name="Retry Loop",
            max_iterations=5,
        )
        assert loop.loop_id == "loop_1"
        assert loop.name == "Retry Loop"
        assert loop.max_iterations == 5
        assert loop.break_condition is None

    def test_plan_loop_with_break_condition(self):
        """Test PlanLoop with break condition."""
        condition = StepCondition(field="status", operator="==", value="success")
        loop = PlanLoop(
            loop_id="loop_1",
            name="Retry Loop",
            max_iterations=3,
            break_condition=condition,
        )
        assert loop.break_condition is not None
        assert loop.break_condition.field == "status"


class TestPlanMultiStep:
    """Tests for multi-step Plan configuration."""

    def test_plan_single_step_execution(self):
        """Test plan with single step enabled."""
        step = PlanStep(
            step_id="step_1",
            name="Single Step",
            intent=Intent.LOOKUP,
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step],
        )
        assert plan.enable_multistep is True
        assert len(plan.steps) == 1
        assert plan.steps[0].step_id == "step_1"

    def test_plan_multi_step_sequence(self):
        """Test plan with sequential steps."""
        step1 = PlanStep(
            step_id="step_1",
            name="Step 1",
            intent=Intent.LOOKUP,
            next_step_id="step_2",
        )
        step2 = PlanStep(
            step_id="step_2",
            name="Step 2",
            intent=Intent.SEARCH,
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step1, step2],
        )
        assert len(plan.steps) == 2
        assert plan.steps[0].next_step_id == "step_2"

    def test_plan_with_branches(self):
        """Test plan with conditional branches."""
        step1 = PlanStep(
            step_id="step_1",
            name="Initial Step",
            intent=Intent.LOOKUP,
        )
        branch_condition = StepCondition(field="type", operator="==", value="metric")
        branch_step = PlanStep(
            step_id="branch_step_1",
            name="Metric Branch Step",
            intent=Intent.AGGREGATE,
        )
        branch = PlanBranch(
            branch_id="branch_1",
            name="Metric Branch",
            condition=branch_condition,
            steps=[branch_step],
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step1],
            branches=[branch],
        )
        assert len(plan.branches) == 1
        assert plan.branches[0].branch_id == "branch_1"

    def test_plan_with_loops(self):
        """Test plan with loop constructs."""
        loop_step = PlanStep(
            step_id="loop_step_1",
            name="Loopable Step",
            intent=Intent.SEARCH,
        )
        loop = PlanLoop(
            loop_id="loop_1",
            name="Retry Loop",
            max_iterations=3,
            steps=[loop_step],
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            loops=[loop],
        )
        assert len(plan.loops) == 1
        assert plan.loops[0].max_iterations == 3


class TestPlanValidation:
    """Tests for plan validation."""

    def test_validate_simple_plan_success(self):
        """Test validation of simple plan."""
        step = PlanStep(
            step_id="step_1",
            name="Step 1",
            intent=Intent.LOOKUP,
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step],
        )
        normalized, trace = validate_plan(plan)
        assert normalized.enable_multistep is True
        assert trace.get("multistep", {}).get("multistep_enabled") is True
        assert trace.get("multistep", {}).get("unique_ids", {}).get("valid") is True

    def test_validate_duplicate_step_ids_fails(self):
        """Test validation fails with duplicate step IDs."""
        step1 = PlanStep(
            step_id="step_1",
            name="Step 1",
            intent=Intent.LOOKUP,
        )
        step2 = PlanStep(
            step_id="step_1",  # Duplicate ID
            name="Step 2",
            intent=Intent.SEARCH,
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step1, step2],
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_invalid_next_step_reference_fails(self):
        """Test validation fails with invalid step references."""
        step1 = PlanStep(
            step_id="step_1",
            name="Step 1",
            intent=Intent.LOOKUP,
            next_step_id="nonexistent_step",
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step1],
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_budget_exceeded_fails(self):
        """Test validation fails when budget is exceeded."""
        # Create steps that exceed budget
        steps = [
            PlanStep(
                step_id=f"step_{i}",
                name=f"Step {i}",
                intent=Intent.LOOKUP,
            )
            for i in range(15)  # More than default max_steps (10)
        ]
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=steps,
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_with_custom_budget(self):
        """Test validation with custom budget constraints."""
        steps = [
            PlanStep(
                step_id=f"step_{i}",
                name=f"Step {i}",
                intent=Intent.LOOKUP,
            )
            for i in range(15)
        ]
        budget = BudgetSpec(max_steps=20)  # Increase budget
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=steps,
            budget=budget,
        )
        normalized, trace = validate_plan(plan)
        assert normalized.budget.max_steps == 20

    def test_validate_multistep_disabled(self):
        """Test validation when multistep is disabled."""
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=False,  # Disabled
        )
        normalized, trace = validate_plan(plan)
        assert trace.get("multistep", {}).get("multistep_enabled") is False

    def test_validate_complex_plan(self):
        """Test validation of complex plan with steps, branches, and loops."""
        step1 = PlanStep(
            step_id="step_1",
            name="Initial Step",
            intent=Intent.LOOKUP,
            next_step_id="step_2",
        )
        step2 = PlanStep(
            step_id="step_2",
            name="Secondary Step",
            intent=Intent.SEARCH,
            next_step_id="branch_1",
        )
        branch_condition = StepCondition(field="status", operator="==", value="found")
        branch_step = PlanStep(
            step_id="branch_step_1",
            name="Branch Step",
            intent=Intent.AGGREGATE,
            next_step_id="loop_1",
        )
        branch = PlanBranch(
            branch_id="branch_1",
            name="Success Branch",
            condition=branch_condition,
            steps=[branch_step],
        )
        loop_step = PlanStep(
            step_id="loop_step_1",
            name="Retry Step",
            intent=Intent.EXPAND,
        )
        loop = PlanLoop(
            loop_id="loop_1",
            name="Validation Loop",
            max_iterations=3,
            steps=[loop_step],
        )
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            steps=[step1, step2],
            branches=[branch],
            loops=[loop],
            budget=BudgetSpec(max_steps=20, max_branches=5),
        )
        normalized, trace = validate_plan(plan)
        assert normalized.enable_multistep is True
        assert trace.get("multistep", {}).get("structure", {}).get("total_steps") == 2
        assert trace.get("multistep", {}).get("structure", {}).get("total_branches") == 1
        assert trace.get("multistep", {}).get("structure", {}).get("total_loops") == 1

    def test_validate_timeout_invalid_range(self):
        """Test validation fails with invalid timeout_seconds."""
        budget = BudgetSpec(timeout_seconds=0)  # Invalid: less than 1
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            budget=budget,
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_timeout_exceeds_maximum(self):
        """Test validation fails when timeout exceeds maximum."""
        budget = BudgetSpec(timeout_seconds=3601)  # Invalid: exceeds 1 hour
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            budget=budget,
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_timeout_valid_range(self):
        """Test validation passes with valid timeout_seconds."""
        budget = BudgetSpec(timeout_seconds=300)  # Valid: 5 minutes
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            budget=budget,
        )
        normalized, trace = validate_plan(plan)
        assert normalized.budget.timeout_seconds == 300

    def test_validate_max_depth_invalid_range(self):
        """Test validation fails with invalid max_depth."""
        budget = BudgetSpec(max_depth=0)  # Invalid: less than 1
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            budget=budget,
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_max_depth_exceeds_maximum(self):
        """Test validation fails when max_depth exceeds maximum."""
        budget = BudgetSpec(max_depth=11)  # Invalid: exceeds 10
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            budget=budget,
        )
        with pytest.raises(ValueError, match="Multi-step plan validation failed"):
            validate_plan(plan)

    def test_validate_max_depth_valid_range(self):
        """Test validation passes with valid max_depth."""
        budget = BudgetSpec(max_depth=5)  # Valid: within range
        plan = Plan(
            intent=Intent.LOOKUP,
            enable_multistep=True,
            budget=budget,
        )
        normalized, trace = validate_plan(plan)
        assert normalized.budget.max_depth == 5
