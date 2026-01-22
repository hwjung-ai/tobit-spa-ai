#!/usr/bin/env python3
"""
Simple test script for StageExecutor and PlanOutput implementation.
"""

import sys

sys.path.append('/home/spa/tobit-spa-ai/apps/api')

import asyncio

from app.modules.ops.schemas import StageInput
from app.modules.ops.services.ci.orchestrator.stage_executor import StageExecutor
from app.modules.ops.services.ci.planner.plan_schema import (
    Plan,
    PlanOutput,
    PlanOutputKind,
)


async def test_stage_executor():
    """Test the StageExecutor with a simple plan output."""
    print("Testing StageExecutor...")

    # Create a simple PlanOutput
    plan_output = PlanOutput(
        kind=PlanOutputKind.PLAN,
        plan=Plan(
            intent="LOOKUP",
            primary={"keywords": ["test"]},
            secondary={"keywords": ["example"]}
        ),
        confidence=1.0,
        reasoning="Test plan"
    )

    # Create StageInput
    stage_input = StageInput(
        stage="route_plan",
        applied_assets={"prompt": "test:1"},
        params={"plan_output": plan_output.model_dump()}
    )

    # Create StageExecutor
    executor = StageExecutor()

    # Execute the stage
    try:
        result = await executor.execute_stage(stage_input)
        print(f"✓ Stage execution successful: {result.stage}")
        print(f"  Status: {result.diagnostics.status}")
        print(f"  Duration: {result.duration_ms}ms")
        print(f"  References: {len(result.references)}")
        return True
    except Exception as e:
        print(f"✗ Stage execution failed: {str(e)}")
        return False

async def test_direct_answer():
    """Test direct answer path."""
    print("\nTesting direct answer...")

    from app.modules.ops.services.ci.planner.plan_schema import DirectAnswerPayload

    plan_output = PlanOutput(
        kind=PlanOutputKind.DIRECT,
        direct_answer=DirectAnswerPayload(
            answer="Hello! This is a test direct answer.",
            confidence=0.95,
            reasoning="Simple greeting"
        ),
        confidence=0.95,
        reasoning="Direct answer test"
    )

    stage_input = StageInput(
        stage="route_plan",
        applied_assets={},
        params={"plan_output": plan_output.model_dump()}
    )

    executor = StageExecutor()

    try:
        result = await executor.execute_stage(stage_input)
        print(f"✓ Direct answer execution successful: {result.stage}")
        print(f"  Status: {result.diagnostics.status}")
        return True
    except Exception as e:
        print(f"✗ Direct answer execution failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("Phase 1 Implementation Tests")
    print("=" * 40)

    test1 = await test_stage_executor()
    test2 = await test_direct_answer()

    print("\n" + "=" * 40)
    if test1 and test2:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))