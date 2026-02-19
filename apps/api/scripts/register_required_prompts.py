"""
Register required prompt assets to database.

This script registers the following prompts:
1. ops_all - OPS ALL mode planning and summary
2. tool_selector - Generic tool selection prompt

Usage:
    python scripts/register_required_prompts.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from core.logging import get_logger

logger = get_logger(__name__)

# OPS ALL prompt templates
OPS_ALL_PROMPT = {
    "name": "ops_all",
    "description": "OPS ALL mode planning and summary prompts",
    "templates": {
        "plan_system": """당신은 OPS(운영) 질문을 분석하여 실행 계획을 수립하는 AI입니다.

사용 가능한 실행기:
- config: CI(설정 항목) 조회
- metric: 메트릭/성능 데이터 조회
- hist: 이력/변경 내역 조회
- graph: CI 관계 그래프 조회

응답은 반드시 다음 JSON 형식으로만 출력하세요:
{
  "run_config": true/false,
  "run_metric": true/false,
  "run_hist": true/false,
  "run_graph": true/false,
  "time_hint": "시간 힌트 (예: 최근 1시간, 오늘)" 또는 null,
  "metric_hint": "메트릭 힌트 (예: CPU, 메모리)" 또는 null,
  "ci_hint": "CI 힌트 (예: 서버명, IP)" 또는 null
}

분석 규칙:
1. CI 조회 관련 질문 → run_config: true
2. 성능/메트릭 관련 질문 → run_metric: true
3. 이력/변경 관련 질문 → run_hist: true
4. 관계/연결 관련 질문 → run_graph: true
5. 복합 질문은 여러 실행기를 true로 설정
6. 반드시 유효한 JSON만 출력""",
        "plan_user": """다음 질문을 분석하여 실행 계획을 JSON으로 출력하세요.

질문: {question}

JSON 응답:""",
        "summary_system": """당신은 OPS 실행 결과를 종합하여 사용자에게 유용한 요약을 제공하는 AI입니다.

실행 결과를 바탕으로:
1. 질문에 대한 직접적인 답변 제공
2. 중요한 발견 사항 요약
3. 추가로 확인할 수 있는 정보 제안

응답은 한국어로 작성하고, 마크다운 형식을 사용하세요.""",
        "summary_user": """다음 질문과 실행 결과를 바탕으로 요약을 작성하세요.

질문: {question}

실행 계획: {plan}

실행 결과:
{evidence}

요약:""",
    },
}

# Tool selector prompt templates
TOOL_SELECTOR_PROMPT = {
    "name": "tool_selector",
    "description": "Generic tool selection prompt for LLM-based tool selection",
    "template": """당신은 사용자 질문에 적합한 도구(Tool)를 선택하는 AI입니다.

사용 가능한 도구 목록:
{tool_descriptions}

사용자 질문:
{question}

응답 형식 (반드시 JSON으로만 응답):
{{
  "tools": [
    {{
      "tool_name": "도구 이름",
      "confidence": 0.0~1.0 사이의 신뢰도,
      "reasoning": "선택 이유",
      "parameters": {{"파라미터명": "값"}}
    }}
  ],
  "execution_order": "sequential" 또는 "parallel"
}}

주의사항:
1. 질문에 가장 적합한 도구를 선택하세요
2. 여러 도구가 필요하면 모두 선택하세요
3. 도구 순서가 중요하면 sequential, 독립적이면 parallel로 지정하세요
4. 파라미터는 질문에서 추출할 수 있는 값만 포함하세요
5. 반드시 유효한 JSON만 출력하세요

JSON 응답:""",
}


def register_prompt_asset(
    session,
    scope: str,
    engine: str,
    name: str,
    description: str,
    payload: dict,
) -> TbAssetRegistry:
    """Register a prompt asset to database."""
    # Check if already exists
    existing = (
        session.query(TbAssetRegistry)
        .filter(
            TbAssetRegistry.asset_type == "prompt",
            TbAssetRegistry.scope == scope,
            TbAssetRegistry.name == name,
        )
        .first()
    )

    if existing:
        logger.info(f"Updating existing prompt asset: {name}")
        existing.output_contract = payload  # Templates go in output_contract
        existing.engine = engine  # Update engine field
        existing.description = description
        existing.status = "published"  # Ensure published
        existing.is_system = True
        session.add(existing)
        return existing

    logger.info(f"Creating new prompt asset: {name}")
    asset = TbAssetRegistry(
        tenant_id="",  # Empty for global visibility
        asset_type="prompt",
        scope=scope,
        engine=engine,  # Use engine field (not tool_type)
        name=name,
        description=description,
        status="published",  # Must be published to be loaded
        output_contract=payload,  # Templates go in output_contract
        is_system=False,  # NOT system asset for UI visibility
    )
    session.add(asset)
    return asset


def migrate_ci_to_ops_names(session):
    """Migrate old ci_* prompt names to ops_* names."""
    # Update ci_planner_output_parser -> ops_planner_output_parser
    old_planner = (
        session.query(TbAssetRegistry)
        .filter(
            TbAssetRegistry.asset_type == "prompt",
            TbAssetRegistry.name == "ci_planner_output_parser",
        )
        .first()
    )
    if old_planner:
        logger.info("Migrating ci_planner_output_parser -> ops_planner_output_parser")
        old_planner.name = "ops_planner_output_parser"
        old_planner.scope = "ops"
        session.add(old_planner)

    # Update ci_compose_summary -> ops_compose_summary
    old_compose = (
        session.query(TbAssetRegistry)
        .filter(
            TbAssetRegistry.asset_type == "prompt",
            TbAssetRegistry.name == "ci_compose_summary",
        )
        .first()
    )
    if old_compose:
        logger.info("Migrating ci_compose_summary -> ops_compose_summary")
        old_compose.name = "ops_compose_summary"
        old_compose.scope = "ops"
        session.add(old_compose)


def main():
    """Register all required prompt assets."""
    logger.info("Starting prompt asset registration...")

    with get_session_context() as session:
        # Migrate old ci_* names to ops_*
        migrate_ci_to_ops_names(session)

        # Register ops_all prompt
        register_prompt_asset(
            session=session,
            scope="ops",
            engine="ops_all",
            name="ops_all",
            description=OPS_ALL_PROMPT["description"],
            payload=OPS_ALL_PROMPT,
        )

        # Register tool_selector prompt
        register_prompt_asset(
            session=session,
            scope="generic",
            engine="openai",
            name="tool_selector",
            description=TOOL_SELECTOR_PROMPT["description"],
            payload=TOOL_SELECTOR_PROMPT,
        )

        session.commit()
        logger.info("Prompt assets registered successfully!")

    print("✅ Registered prompt assets:")
    print("   - ops_all (scope=ops, engine=ops_all)")
    print("   - tool_selector (scope=generic, engine=openai)")
    print("   - ops_planner_output_parser (migrated from ci_planner_output_parser)")
    print("   - ops_compose_summary (migrated from ci_compose_summary)")


if __name__ == "__main__":
    main()