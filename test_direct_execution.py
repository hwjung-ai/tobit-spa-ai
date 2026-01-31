#!/usr/bin/env python
"""
Direct execution test to get trace_id and analyze results.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

import asyncio
from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner
from app.modules.ops.services.ci.planner.planner_llm import create_plan_output

async def main():
    question = '전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘'

    print(f'Question: {question}')
    print('=' * 80)

    # Generate plan (sync function)
    plan_output = create_plan_output(question)

    if plan_output.kind != 'plan':
        print(f'Plan generation failed: {plan_output.kind}')
        return None

    plan = plan_output.plan
    plan_raw = plan.model_dump()

    print(f'Plan created successfully')
    print(f'  execution_strategy: {plan.execution_strategy}')
    print(f'  primary.tool_type: {plan.primary.tool_type if plan.primary else None}')
    print(f'  history.enabled: {plan.history.enabled if plan.history else None}')

    # Create runner
    runner = CIOrchestratorRunner(
        tenant_id='default',
        plan=plan,
        plan_raw=plan_raw,
        question=question,
        policy_trace={},
        user_id='test_user',
        request_id='manual_test_002'
    )

    # Execute
    print('\nExecuting...')
    result = await runner.run()

    print(f'\n' + '=' * 80)
    print(f'RESULT')
    print('=' * 80)
    print(f'Trace ID: {result.trace_id}')
    print(f'Status: {result.status}')
    print(f'Error: {result.error}')
    print(f'Summary: {result.summary[:300] if result.summary else "No summary"}...')
    print(f'Blocks: {len(result.blocks)}')

    return result.trace_id

if __name__ == "__main__":
    trace_id = asyncio.run(main())
    print(f'\n\nTRACE_ID for analysis: {trace_id}')
