# AI 에이전트용 구현 명세서

> **목적**: AI 에이전트가 즉시 코드 작성에 착수할 수 있도록 파일별, 함수별 상세 구현 명세를 제공한다.

---

## 목차

1. [Phase 1 상세 구현 명세](#phase-1-상세-구현-명세)
2. [Phase 2 상세 구현 명세](#phase-2-상세-구현-명세)
3. [Phase 3 상세 구현 명세](#phase-3-상세-구현-명세)
4. [테스트 명세](#테스트-명세)

---

# Phase 1 상세 구현 명세

## 1.1 Backend: PlanOutput 스키마

### 파일: `apps/api/app/modules/ops/services/ci/planner/plan_output.py` (신규 생성)

```python
"""
Route+Plan 단계의 통합 출력 계약.
모든 질의는 이 구조로 분기된다.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import time


class PlanOutputKind(str, Enum):
    """Plan 출력 종류"""
    DIRECT = "direct"      # 즉시 응답 (데이터 조회 불필요)
    PLAN = "plan"          # 오케스트레이션 필요
    REJECT = "reject"      # 정책 거부


class DirectAnswerPayload(BaseModel):
    """DirectAnswer 전용 페이로드"""
    answer_text: str = Field(..., description="즉시 응답 텍스트")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="신뢰도")
    source: str = Field(default="knowledge", description="응답 소스: knowledge|cache|fallback")
    references: List[Dict[str, Any]] = Field(default_factory=list, description="참조 목록")

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {'knowledge', 'cache', 'fallback'}
        if v not in allowed:
            raise ValueError(f"source must be one of {allowed}")
        return v


class RejectPayload(BaseModel):
    """Reject 전용 페이로드"""
    reason: str = Field(..., description="거부 사유")
    policy_id: Optional[str] = Field(default=None, description="적용된 정책 ID")
    suggestion: Optional[str] = Field(default=None, description="대안 제시")


class PlanOutput(BaseModel):
    """
    Route+Plan 단계의 통합 출력 계약.
    모든 질의는 이 구조로 분기된다.

    사용 예:
    ```python
    # Direct Answer
    output = PlanOutput(
        kind=PlanOutputKind.DIRECT,
        direct=DirectAnswerPayload(answer_text="안녕하세요!", confidence=1.0)
    )

    # Orchestration Plan
    output = PlanOutput(
        kind=PlanOutputKind.PLAN,
        plan=Plan(intent=Intent.LOOKUP, ...)
    )

    # Reject
    output = PlanOutput(
        kind=PlanOutputKind.REJECT,
        reject=RejectPayload(reason="삭제 작업은 지원하지 않습니다")
    )
    ```
    """
    kind: PlanOutputKind = Field(..., description="출력 종류")

    # kind == DIRECT
    direct: Optional[DirectAnswerPayload] = Field(default=None)

    # kind == PLAN (기존 Plan 모델 사용)
    plan: Optional["Plan"] = Field(default=None)

    # kind == REJECT
    reject: Optional[RejectPayload] = Field(default=None)

    # 공통 메타데이터
    routing_reasoning: str = Field(default="", description="라우팅 결정 이유")
    elapsed_ms: int = Field(default=0, description="처리 시간 (ms)")

    def model_post_init(self, __context: Any) -> None:
        """Pydantic v2 post-init validation"""
        self.validate_consistency()

    def validate_consistency(self) -> None:
        """kind와 payload 일관성 검증"""
        if self.kind == PlanOutputKind.DIRECT:
            if self.direct is None:
                raise ValueError("kind=direct requires direct payload")
            if self.plan is not None or self.reject is not None:
                raise ValueError("kind=direct should not have plan or reject payload")
        elif self.kind == PlanOutputKind.PLAN:
            if self.plan is None:
                raise ValueError("kind=plan requires plan payload")
            if self.direct is not None or self.reject is not None:
                raise ValueError("kind=plan should not have direct or reject payload")
        elif self.kind == PlanOutputKind.REJECT:
            if self.reject is None:
                raise ValueError("kind=reject requires reject payload")
            if self.direct is not None or self.plan is not None:
                raise ValueError("kind=reject should not have direct or plan payload")

    def is_direct(self) -> bool:
        """Direct answer 여부"""
        return self.kind == PlanOutputKind.DIRECT

    def is_orchestration(self) -> bool:
        """Orchestration 필요 여부"""
        return self.kind == PlanOutputKind.PLAN

    def is_reject(self) -> bool:
        """Reject 여부"""
        return self.kind == PlanOutputKind.REJECT

    def get_route_label(self) -> str:
        """Trace에 저장할 route 레이블"""
        return {
            PlanOutputKind.DIRECT: "direct",
            PlanOutputKind.PLAN: "orch",
            PlanOutputKind.REJECT: "reject"
        }[self.kind]


# Forward reference 해결을 위해 Plan import
from .plan_schema import Plan
PlanOutput.model_rebuild()
```

---

## 1.2 Backend: Stage Input/Output 스키마

### 파일: `apps/api/app/modules/ops/schemas.py` (수정)

아래 클래스들을 파일 상단에 추가:

```python
# === Stage In/Out Schemas (신규 추가) ===

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class StageDiagnostics(BaseModel):
    """Stage 실행 진단 정보"""
    status: str = Field(..., description="ok|warning|error")
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    empty_flags: Dict[str, bool] = Field(
        default_factory=dict,
        description="빈 결과 플래그 (e.g., {'result_empty': True})"
    )
    counts: Dict[str, int] = Field(
        default_factory=dict,
        description="카운트 정보 (e.g., {'rows': 0, 'references': 5})"
    )

    @classmethod
    def ok(cls, counts: Dict[str, int] = None) -> "StageDiagnostics":
        return cls(status="ok", counts=counts or {})

    @classmethod
    def warning(cls, warnings: List[str], counts: Dict[str, int] = None) -> "StageDiagnostics":
        return cls(status="warning", warnings=warnings, counts=counts or {})

    @classmethod
    def error(cls, errors: List[str]) -> "StageDiagnostics":
        return cls(status="error", errors=errors)


class StageInput(BaseModel):
    """Stage 입력 정보"""
    stage: str = Field(..., description="stage 이름: route_plan|validate|execute|compose|present")
    applied_assets: Dict[str, str] = Field(
        default_factory=dict,
        description="적용된 asset 목록 (asset_type -> asset_id:version)"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="stage 입력 파라미터"
    )
    prev_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="이전 stage 출력 (첫 번째 stage는 None)"
    )


class StageOutput(BaseModel):
    """Stage 출력 정보"""
    stage: str = Field(..., description="stage 이름")
    result: Dict[str, Any] = Field(..., description="stage 실행 결과")
    diagnostics: StageDiagnostics = Field(..., description="진단 정보")
    references: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="생성된 references"
    )
    duration_ms: int = Field(..., description="실행 시간 (ms)")


# === CiAskRequest 수정 ===

class CiAskRequest(BaseModel):
    """CI Ask 요청 (수정됨)"""
    question: str = Field(..., description="사용자 질문")
    rerun: Optional["RerunRequest"] = Field(default=None, description="재실행 요청")

    # 신규 추가
    test_mode: bool = Field(default=False, description="테스트 모드 여부")
    asset_overrides: Dict[str, str] = Field(
        default_factory=dict,
        description="asset override 목록 (stage:asset_key -> asset_id:version)"
    )
    baseline_trace_id: Optional[str] = Field(
        default=None,
        description="비교 기준 trace ID"
    )
```

---

## 1.3 Backend: Trace 모델 확장

### 파일: `apps/api/app/modules/inspector/models.py` (수정)

`TbExecutionTrace` 클래스에 다음 필드 추가:

```python
from sqlmodel import Field, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Dict, Any, Optional


class TbExecutionTrace(SQLModel, table=True):
    """실행 트레이스 (수정됨)"""
    __tablename__ = "tb_execution_traces"

    # 기존 필드들...
    trace_id: str = Field(primary_key=True)
    parent_trace_id: Optional[str] = Field(default=None)
    feature: str = Field(default="ops")
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ops_mode: Optional[str] = None
    question: Optional[str] = None
    status: str = Field(default="pending")
    duration_ms: Optional[int] = None

    # 기존 JSONB 필드들...
    plan_raw: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    plan_validated: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    execution_steps: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))
    answer: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    applied_assets: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    asset_versions: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    fallbacks: Dict[str, bool] = Field(default_factory=dict, sa_column=Column(JSONB))
    flow_spans: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))
    ui_render: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    audit_links: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))

    # === 신규 필드 추가 ===
    route: str = Field(
        default="orch",
        description="라우팅 결과: direct|orch|reject"
    )
    stage_inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
        description="Stage별 입력 정보"
    )
    stage_outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
        description="Stage별 출력 정보"
    )
    replan_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
        description="Replan 이벤트 목록"
    )

    # 테스트 모드 관련
    test_mode: bool = Field(default=False)
    asset_overrides: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSONB)
    )
    baseline_trace_id: Optional[str] = Field(default=None)

    # 타임스탬프
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
```

---

## 1.4 Backend: DB 마이그레이션

### 파일: `apps/api/alembic/versions/xxx_add_stage_tracking.py` (신규 생성)

```python
"""Add stage tracking columns to execution_traces

Revision ID: add_stage_tracking
Revises: [이전 revision]
Create Date: 2026-01-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = 'add_stage_tracking'
down_revision = None  # 이전 revision ID로 교체
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column(
        'tb_execution_traces',
        sa.Column('route', sa.String(20), nullable=False, server_default='orch')
    )
    op.add_column(
        'tb_execution_traces',
        sa.Column('stage_inputs', JSONB, nullable=False, server_default='[]')
    )
    op.add_column(
        'tb_execution_traces',
        sa.Column('stage_outputs', JSONB, nullable=False, server_default='[]')
    )
    op.add_column(
        'tb_execution_traces',
        sa.Column('replan_events', JSONB, nullable=False, server_default='[]')
    )
    op.add_column(
        'tb_execution_traces',
        sa.Column('test_mode', sa.Boolean, nullable=False, server_default='false')
    )
    op.add_column(
        'tb_execution_traces',
        sa.Column('asset_overrides', JSONB, nullable=False, server_default='{}')
    )
    op.add_column(
        'tb_execution_traces',
        sa.Column('baseline_trace_id', sa.String(100), nullable=True)
    )

    # Add indexes
    op.create_index('idx_traces_route', 'tb_execution_traces', ['route'])
    op.create_index(
        'idx_traces_replan_events',
        'tb_execution_traces',
        ['replan_events'],
        postgresql_using='gin'
    )
    op.create_index('idx_traces_test_mode', 'tb_execution_traces', ['test_mode'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_traces_test_mode')
    op.drop_index('idx_traces_replan_events')
    op.drop_index('idx_traces_route')

    # Drop columns
    op.drop_column('tb_execution_traces', 'baseline_trace_id')
    op.drop_column('tb_execution_traces', 'asset_overrides')
    op.drop_column('tb_execution_traces', 'test_mode')
    op.drop_column('tb_execution_traces', 'replan_events')
    op.drop_column('tb_execution_traces', 'stage_outputs')
    op.drop_column('tb_execution_traces', 'stage_inputs')
    op.drop_column('tb_execution_traces', 'route')
```

---

## 1.5 Backend: Planner 수정

### 파일: `apps/api/app/modules/ops/services/ci/planner/planner_llm.py` (수정)

기존 `create_plan()` 함수를 `create_plan_output()`으로 확장:

```python
# 파일 상단에 import 추가
from .plan_output import PlanOutput, PlanOutputKind, DirectAnswerPayload, RejectPayload
import time


# 신규 함수 추가 (기존 create_plan 유지, 새 함수 추가)
async def create_plan_output(
    question: str,
    tenant_id: str,
    context: Optional[Dict[str, Any]] = None
) -> PlanOutput:
    """
    질문을 분석하여 PlanOutput 반환.

    LLM을 호출하여 다음 중 하나를 결정:
    - DirectAnswer: 간단한 인사, 도움말 등
    - OrchestrationPlan: 데이터 조회 필요
    - Reject: 정책 위반 질문

    Args:
        question: 사용자 질문
        tenant_id: 테넌트 ID
        context: 추가 컨텍스트 (선택)

    Returns:
        PlanOutput: 라우팅 결정 및 페이로드
    """
    start_time = time.time()

    # 1. 빠른 규칙 기반 체크 (LLM 호출 전)
    quick_result = _check_quick_rules(question)
    if quick_result:
        return quick_result

    # 2. LLM 호출하여 라우팅 결정
    try:
        routing_result = await _call_routing_llm(question, tenant_id, context)
    except Exception as e:
        # LLM 실패 시 fallback: 기존 Plan 생성 시도
        logger.warning(f"Routing LLM failed, falling back to plan creation: {e}")
        plan = await create_plan(question, tenant_id)
        return PlanOutput(
            kind=PlanOutputKind.PLAN,
            plan=plan,
            routing_reasoning="LLM routing failed, defaulted to orchestration",
            elapsed_ms=int((time.time() - start_time) * 1000)
        )

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 3. 라우팅 결과에 따른 PlanOutput 생성
    if routing_result["kind"] == "direct":
        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct=DirectAnswerPayload(
                answer_text=routing_result["answer"],
                confidence=routing_result.get("confidence", 0.9),
                source="knowledge"
            ),
            routing_reasoning=routing_result.get("reasoning", ""),
            elapsed_ms=elapsed_ms
        )

    elif routing_result["kind"] == "reject":
        return PlanOutput(
            kind=PlanOutputKind.REJECT,
            reject=RejectPayload(
                reason=routing_result["reason"],
                policy_id=routing_result.get("policy_id"),
                suggestion=routing_result.get("suggestion")
            ),
            routing_reasoning=routing_result.get("reasoning", ""),
            elapsed_ms=elapsed_ms
        )

    else:  # "plan"
        # 기존 create_plan 호출
        plan = await create_plan(question, tenant_id)
        return PlanOutput(
            kind=PlanOutputKind.PLAN,
            plan=plan,
            routing_reasoning=routing_result.get("reasoning", "Data lookup required"),
            elapsed_ms=elapsed_ms
        )


def _check_quick_rules(question: str) -> Optional[PlanOutput]:
    """빠른 규칙 기반 체크 (LLM 호출 없이)"""
    q_lower = question.strip().lower()

    # 인사말 패턴
    greeting_patterns = ["안녕", "hello", "hi", "반가워", "처음 뵙"]
    if any(p in q_lower for p in greeting_patterns) and len(q_lower) < 30:
        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct=DirectAnswerPayload(
                answer_text="안녕하세요! 무엇을 도와드릴까요?",
                confidence=1.0,
                source="knowledge"
            ),
            routing_reasoning="Detected greeting pattern"
        )

    # 도움말 패턴
    help_patterns = ["도움말", "help", "사용법", "어떻게 사용"]
    if any(p in q_lower for p in help_patterns):
        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct=DirectAnswerPayload(
                answer_text="저는 설비 정보 조회, 메트릭 분석, 이력 검색 등을 도와드립니다. "
                           "예: 'GT-01 상태 알려줘', '최근 알람 이력 보여줘'",
                confidence=1.0,
                source="knowledge"
            ),
            routing_reasoning="Detected help request pattern"
        )

    # 삭제/수정 등 금지 패턴
    forbidden_patterns = ["삭제해", "지워", "delete", "remove", "drop", "변경해", "수정해"]
    if any(p in q_lower for p in forbidden_patterns):
        return PlanOutput(
            kind=PlanOutputKind.REJECT,
            reject=RejectPayload(
                reason="데이터 변경 작업은 지원하지 않습니다.",
                policy_id="readonly_policy",
                suggestion="조회 작업만 가능합니다. 예: 'GT-01 정보 조회'"
            ),
            routing_reasoning="Detected forbidden operation pattern"
        )

    return None


async def _call_routing_llm(
    question: str,
    tenant_id: str,
    context: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    LLM을 호출하여 라우팅 결정.

    Returns:
        {
            "kind": "direct" | "plan" | "reject",
            "answer": "...",  # direct일 때
            "reason": "...",  # reject일 때
            "reasoning": "...",  # 판단 근거
            "confidence": 0.9
        }
    """
    # Prompt 로드
    from ...asset_registry.loader import load_prompt_asset
    prompt_data = load_prompt_asset("ci", "router", "route_decision")

    # LLM 호출 (기존 _call_output_parser_llm 재사용)
    system_prompt = prompt_data.get("template", DEFAULT_ROUTER_PROMPT)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    # OpenAI 호출
    from openai import AsyncOpenAI
    client = AsyncOpenAI()

    response = await client.chat.completions.create(
        model="gpt-4o-mini",  # 빠른 라우팅용
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=500,
        temperature=0.1
    )

    result = json.loads(response.choices[0].message.content)
    return result


# 기본 라우터 프롬프트
DEFAULT_ROUTER_PROMPT = """You are a query router for an industrial equipment management system.

Analyze the user's question and decide the routing:

1. "direct" - For greetings, help requests, or questions answerable without data lookup
2. "plan" - For questions requiring data lookup (equipment status, metrics, history, etc.)
3. "reject" - For forbidden operations (delete, modify, drop, etc.)

Respond in JSON format:
{
    "kind": "direct" | "plan" | "reject",
    "answer": "...",  // Only for kind=direct
    "reason": "...",  // Only for kind=reject
    "suggestion": "...",  // Only for kind=reject
    "reasoning": "...",  // Why this routing was chosen
    "confidence": 0.0-1.0
}

Examples of "plan" queries:
- "GT-01 상태 알려줘" -> data lookup needed
- "최근 알람 이력" -> history query needed
- "CPU 사용률 그래프" -> metrics needed

Examples of "direct" queries:
- "안녕하세요" -> greeting
- "도움말" -> help request
- "이 시스템은 뭐야?" -> general info
"""
```

---

## 1.6 Backend: Stage Executor

### 파일: `apps/api/app/modules/ops/services/stage_executor.py` (신규 생성)

```python
"""
Stage Executor - Pipeline Stage를 순차 실행하고 In/Out을 추적
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import time
import uuid
import logging

from .ci.planner.plan_output import PlanOutput, PlanOutputKind
from .ci.planner.plan_schema import Plan
from .ci.planner.validator import validate_plan
from ..schemas import StageInput, StageOutput, StageDiagnostics
from ..asset_registry.asset_context import get_tracked_assets, track_query_asset


logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Stage 실행 컨텍스트"""
    tenant_id: str
    question: str
    trace_id: str
    user_id: Optional[str] = None
    rerun_context: Optional[Dict[str, Any]] = None
    test_mode: bool = False
    asset_overrides: Dict[str, str] = field(default_factory=dict)

    def get_override(self, stage: str, asset_type: str, default_key: str) -> str:
        """Asset override 조회"""
        override_key = f"{stage}:{asset_type}:{default_key}"
        if override_key in self.asset_overrides:
            return self.asset_overrides[override_key]

        # Stage 없이 조회
        simple_key = f"{asset_type}:{default_key}"
        if simple_key in self.asset_overrides:
            return self.asset_overrides[simple_key]

        return f"{default_key}:published"


class StageExecutor:
    """
    파이프라인 Stage를 순차 실행하고 In/Out을 추적하는 실행기.
    Control Loop와 협력하여 재시도를 처리한다.
    """

    STAGES = ["route_plan", "validate", "execute", "compose", "present"]

    # Stage별 사용 Asset 매핑
    STAGE_ASSETS = {
        "route_plan": ["prompt", "policy", "schema_catalog"],
        "validate": ["policy"],
        "execute": ["query", "source", "mapping"],
        "compose": ["mapping"],
        "present": ["screen"]
    }

    def __init__(self, context: ExecutionContext):
        self.context = context
        self.stage_inputs: List[StageInput] = []
        self.stage_outputs: List[StageOutput] = []
        self.current_stage: Optional[str] = None
        self.tool_calls: List[Dict[str, Any]] = []
        self.references: List[Dict[str, Any]] = []

        # Runner 인스턴스 (lazy init)
        self._runner = None

    async def run_all_stages(
        self,
        plan_output: PlanOutput,
        start_from: str = "validate"
    ) -> Dict[str, Any]:
        """
        모든 Stage를 순차 실행.

        Args:
            plan_output: Route+Plan 결과
            start_from: 시작 stage (기본: validate, route_plan은 이미 완료)

        Returns:
            실행 결과 딕셔너리
        """
        # Route+Plan 결과를 첫 번째 output으로 기록
        self._record_route_plan_output(plan_output)

        if plan_output.kind == PlanOutputKind.DIRECT:
            # Direct Answer: validate → present (execute/compose 스킵)
            await self._run_stage("validate", plan_output)
            await self._run_stage("present", self._get_last_output())
            return self._build_direct_result(plan_output)

        elif plan_output.kind == PlanOutputKind.REJECT:
            # Reject: validate만 실행
            await self._run_stage("validate", plan_output)
            return self._build_reject_result(plan_output)

        else:  # PLAN - Full pipeline
            for stage in ["validate", "execute", "compose", "present"]:
                await self._run_stage(stage, self._get_last_output())

                # Control Loop trigger 확인
                if self._should_trigger_replan():
                    break

        return self._build_result()

    async def run_single_stage(
        self,
        stage: str,
        input_data: Any
    ) -> StageOutput:
        """단일 Stage만 실행 (테스트용)"""
        return await self._run_stage(stage, input_data)

    def _record_route_plan_output(self, plan_output: PlanOutput) -> None:
        """Route+Plan 결과를 stage_outputs에 기록"""
        stage_input = StageInput(
            stage="route_plan",
            applied_assets=self._get_applied_assets("route_plan"),
            params={"question": self.context.question},
            prev_output=None
        )
        self.stage_inputs.append(stage_input)

        stage_output = StageOutput(
            stage="route_plan",
            result={
                "kind": plan_output.kind.value,
                "routing_reasoning": plan_output.routing_reasoning,
                "has_plan": plan_output.plan is not None,
                "has_direct": plan_output.direct is not None,
                "has_reject": plan_output.reject is not None
            },
            diagnostics=StageDiagnostics.ok(),
            references=[],
            duration_ms=plan_output.elapsed_ms
        )
        self.stage_outputs.append(stage_output)

    async def _run_stage(self, stage: str, input_data: Any) -> StageOutput:
        """단일 Stage 실행"""
        self.current_stage = stage
        start_time = time.time()

        # Stage Input 기록
        stage_input = self._build_stage_input(stage, input_data)
        self.stage_inputs.append(stage_input)

        # Stage 실행
        try:
            if stage == "validate":
                result = await self._execute_validate(input_data)
            elif stage == "execute":
                result = await self._execute_execute(input_data)
            elif stage == "compose":
                result = await self._execute_compose(input_data)
            elif stage == "present":
                result = await self._execute_present(input_data)
            else:
                raise ValueError(f"Unknown stage: {stage}")

            diagnostics = self._build_diagnostics(result, "ok")

        except Exception as e:
            logger.exception(f"Stage {stage} failed")
            result = {"error": str(e), "error_type": type(e).__name__}
            diagnostics = StageDiagnostics.error([str(e)])

        # Stage Output 기록
        duration_ms = int((time.time() - start_time) * 1000)
        stage_output = StageOutput(
            stage=stage,
            result=result,
            diagnostics=diagnostics,
            references=result.get("references", []),
            duration_ms=duration_ms
        )
        self.stage_outputs.append(stage_output)

        # References 수집
        if result.get("references"):
            self.references.extend(result["references"])

        return stage_output

    async def _execute_validate(self, input_data: Any) -> Dict[str, Any]:
        """Validate Stage 실행"""
        if isinstance(input_data, PlanOutput):
            if input_data.plan:
                validated, trace = validate_plan(input_data.plan)
                return {
                    "plan_validated": validated.dict() if validated else None,
                    "policy_decisions": trace.get("policy_decisions", []),
                    "validation_passed": True
                }
            else:
                # Direct/Reject는 validation 스킵
                return {"validation_passed": True, "skipped": True}

        # StageOutput에서 plan 추출
        plan_dict = input_data.result.get("plan") if hasattr(input_data, "result") else input_data
        if plan_dict:
            from .ci.planner.plan_schema import Plan
            plan = Plan(**plan_dict)
            validated, trace = validate_plan(plan)
            return {
                "plan_validated": validated.dict(),
                "policy_decisions": trace.get("policy_decisions", [])
            }

        return {"validation_passed": True}

    async def _execute_execute(self, input_data: Any) -> Dict[str, Any]:
        """Execute Stage 실행"""
        # Runner 초기화
        if self._runner is None:
            from .ci.orchestrator.runner import CIOrchestratorRunner
            self._runner = CIOrchestratorRunner(
                tenant_id=self.context.tenant_id,
                trace_id=self.context.trace_id
            )

        # 이전 stage에서 validated plan 추출
        prev_output = input_data.result if hasattr(input_data, "result") else input_data
        plan_dict = prev_output.get("plan_validated") or prev_output.get("plan")

        if not plan_dict:
            return {"error": "No plan to execute", "rows": [], "blocks": []}

        from .ci.planner.plan_schema import Plan
        plan = Plan(**plan_dict)

        # 기존 Runner 로직 호출
        result = await self._runner._execute_plan(plan, self.context.rerun_context)

        # Tool calls 수집
        self.tool_calls.extend(self._runner.tool_calls)

        return {
            "rows": result.get("rows", []),
            "blocks": result.get("blocks", []),
            "tool_calls": [tc.dict() for tc in self._runner.tool_calls],
            "references": result.get("references", [])
        }

    async def _execute_compose(self, input_data: Any) -> Dict[str, Any]:
        """Compose Stage 실행"""
        prev_output = input_data.result if hasattr(input_data, "result") else input_data
        blocks = prev_output.get("blocks", [])

        # Mapping 적용하여 blocks 조합
        # (현재는 execute에서 이미 blocks 생성됨)

        return {
            "blocks": blocks,
            "block_count": len(blocks),
            "references": self._extract_references_from_blocks(blocks)
        }

    async def _execute_present(self, input_data: Any) -> Dict[str, Any]:
        """Present Stage 실행"""
        prev_output = input_data.result if hasattr(input_data, "result") else input_data
        blocks = prev_output.get("blocks", [])

        # Screen asset 로드 (있으면)
        # screen_id = self.context.get_override("present", "screen", "default")

        return {
            "blocks": blocks,
            "screen_applied": False,  # TODO: Screen 적용
            "render_ready": True
        }

    def _build_stage_input(self, stage: str, input_data: Any) -> StageInput:
        """Stage Input 생성"""
        return StageInput(
            stage=stage,
            applied_assets=self._get_applied_assets(stage),
            params=self._extract_params(input_data),
            prev_output=self._get_last_output_dict()
        )

    def _get_applied_assets(self, stage: str) -> Dict[str, str]:
        """Stage별 사용되는 Asset 목록"""
        assets = {}
        asset_types = self.STAGE_ASSETS.get(stage, [])

        for asset_type in asset_types:
            # Context에서 tracked asset 조회
            tracked = get_tracked_assets()
            if asset_type in tracked:
                assets[asset_type] = tracked[asset_type]
            else:
                # 기본값
                assets[asset_type] = self.context.get_override(stage, asset_type, "default")

        return assets

    def _extract_params(self, input_data: Any) -> Dict[str, Any]:
        """입력에서 주요 파라미터 추출"""
        if isinstance(input_data, PlanOutput):
            return {
                "kind": input_data.kind.value,
                "has_plan": input_data.plan is not None
            }
        if isinstance(input_data, StageOutput):
            return {"from_stage": input_data.stage}
        if isinstance(input_data, dict):
            return {k: v for k, v in input_data.items() if k not in ["blocks", "rows"]}
        return {}

    def _get_last_output(self) -> Optional[StageOutput]:
        """마지막 stage output"""
        return self.stage_outputs[-1] if self.stage_outputs else None

    def _get_last_output_dict(self) -> Optional[Dict[str, Any]]:
        """마지막 stage output을 dict로"""
        last = self._get_last_output()
        return last.result if last else None

    def _build_diagnostics(
        self,
        result: Dict[str, Any],
        status: str
    ) -> StageDiagnostics:
        """진단 정보 생성"""
        rows = result.get("rows", result.get("blocks", []))
        is_empty = len(rows) == 0

        return StageDiagnostics(
            status="warning" if is_empty else status,
            warnings=["Empty result"] if is_empty else [],
            errors=[],
            empty_flags={"result_empty": is_empty},
            counts={
                "rows": len(result.get("rows", [])),
                "blocks": len(result.get("blocks", [])),
                "references": len(result.get("references", []))
            }
        )

    def _extract_references_from_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Blocks에서 references 추출"""
        refs = []
        for block in blocks:
            if block.get("type") == "references":
                refs.extend(block.get("items", []))
        return refs

    def _should_trigger_replan(self) -> bool:
        """Replan 트리거 조건 확인"""
        if not self.stage_outputs:
            return False

        last_output = self.stage_outputs[-1]
        diag = last_output.diagnostics

        # Error 상태
        if diag.status == "error":
            return True

        # Empty result (execute stage)
        if last_output.stage == "execute" and diag.empty_flags.get("result_empty"):
            return True

        return False

    def get_replan_trigger(self) -> Optional[str]:
        """현재 Replan 트리거 반환"""
        if not self.stage_outputs:
            return None

        last_output = self.stage_outputs[-1]
        diag = last_output.diagnostics

        if diag.status == "error":
            if "timeout" in str(diag.errors).lower():
                return "TOOL_ERROR_RETRYABLE"
            return "TOOL_ERROR_FATAL"

        if diag.empty_flags.get("result_empty"):
            return "EMPTY_RESULT"

        return None

    def _build_result(self) -> Dict[str, Any]:
        """최종 결과 빌드"""
        last_output = self._get_last_output()
        blocks = last_output.result.get("blocks", []) if last_output else []

        return {
            "blocks": blocks,
            "stage_inputs": [si.dict() for si in self.stage_inputs],
            "stage_outputs": [so.dict() for so in self.stage_outputs],
            "tool_calls": self.tool_calls,
            "references": self.references,
            "route": "orch"
        }

    def _build_direct_result(self, plan_output: PlanOutput) -> Dict[str, Any]:
        """Direct answer 결과 빌드"""
        return {
            "blocks": [{
                "type": "markdown",
                "content": plan_output.direct.answer_text
            }],
            "stage_inputs": [si.dict() for si in self.stage_inputs],
            "stage_outputs": [so.dict() for so in self.stage_outputs],
            "tool_calls": [],
            "references": plan_output.direct.references,
            "route": "direct"
        }

    def _build_reject_result(self, plan_output: PlanOutput) -> Dict[str, Any]:
        """Reject 결과 빌드"""
        return {
            "blocks": [{
                "type": "markdown",
                "content": f"**요청을 처리할 수 없습니다.**\n\n{plan_output.reject.reason}"
                          + (f"\n\n💡 {plan_output.reject.suggestion}" if plan_output.reject.suggestion else "")
            }],
            "stage_inputs": [si.dict() for si in self.stage_inputs],
            "stage_outputs": [so.dict() for so in self.stage_outputs],
            "tool_calls": [],
            "references": [],
            "route": "reject"
        }
```

---

## 1.7 Frontend: OPS Summary Strip 컴포넌트

### 파일: `apps/web/src/components/ops/OpsSummaryStrip.tsx` (신규 생성)

```tsx
/**
 * OPS Summary Strip - 실행 결과 요약 표시
 */

import React from 'react';

interface OpsSummaryStripProps {
  route: 'direct' | 'orch' | 'reject';
  planMode?: string;
  toolCount: number;
  replanCount: number;
  warningCount: number;
  referenceCount: number;
  durationMs: number;
  testMode?: boolean;
}

const routeLabels: Record<string, { label: string; color: string }> = {
  direct: { label: 'DIRECT', color: 'bg-emerald-600' },
  orch: { label: 'ORCH', color: 'bg-sky-600' },
  reject: { label: 'REJECT', color: 'bg-rose-600' },
};

export function OpsSummaryStrip({
  route,
  planMode,
  toolCount,
  replanCount,
  warningCount,
  referenceCount,
  durationMs,
  testMode = false,
}: OpsSummaryStripProps) {
  const routeInfo = routeLabels[route] || routeLabels.orch;

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-slate-800/50 rounded-lg border border-slate-700">
      {/* Route Badge */}
      <div className={`px-2 py-1 rounded text-xs font-semibold ${routeInfo.color}`}>
        {routeInfo.label}
      </div>

      {/* Test Mode Indicator */}
      {testMode && (
        <div className="px-2 py-1 rounded text-xs font-semibold bg-amber-600">
          TEST
        </div>
      )}

      {/* Plan Mode */}
      {planMode && (
        <div className="text-sm text-slate-400">
          Plan: <span className="text-slate-200">{planMode}</span>
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center gap-3 text-sm">
        <StatItem label="Tools" value={toolCount} />
        <StatItem
          label="Replans"
          value={replanCount}
          highlight={replanCount > 0}
        />
        <StatItem
          label="Warnings"
          value={warningCount}
          highlight={warningCount > 0}
          highlightColor="amber"
        />
        <StatItem label="Refs" value={referenceCount} />
      </div>

      {/* Duration */}
      <div className="ml-auto text-sm text-slate-400">
        {durationMs}ms
      </div>
    </div>
  );
}

interface StatItemProps {
  label: string;
  value: number;
  highlight?: boolean;
  highlightColor?: 'sky' | 'amber' | 'rose';
}

function StatItem({ label, value, highlight, highlightColor = 'sky' }: StatItemProps) {
  const colorClass = highlight
    ? highlightColor === 'amber'
      ? 'text-amber-400'
      : highlightColor === 'rose'
      ? 'text-rose-400'
      : 'text-sky-400'
    : 'text-slate-300';

  return (
    <div className="flex items-center gap-1">
      <span className="text-slate-500">{label}:</span>
      <span className={colorClass}>{value}</span>
    </div>
  );
}

export default OpsSummaryStrip;
```

---

## 1.8 Frontend: Stage Timeline 컴포넌트

### 파일: `apps/web/src/components/ops/StageTimeline.tsx` (신규 생성)

```tsx
/**
 * Stage Timeline - Pipeline Stage 시각화
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Check, AlertTriangle, X, RefreshCw } from 'lucide-react';

interface StageInput {
  stage: string;
  applied_assets: Record<string, string>;
  params: Record<string, unknown>;
  prev_output?: Record<string, unknown>;
}

interface StageDiagnostics {
  status: 'ok' | 'warning' | 'error';
  warnings: string[];
  errors: string[];
  empty_flags: Record<string, boolean>;
  counts: Record<string, number>;
}

interface StageOutput {
  stage: string;
  result: Record<string, unknown>;
  diagnostics: StageDiagnostics;
  references: unknown[];
  duration_ms: number;
}

interface ReplanEvent {
  event_id: string;
  trigger: string;
  scope: string;
  decision: string;
  patch?: Record<string, unknown>;
  attempt: number;
  max_attempts: number;
  timestamp_ms: number;
}

interface StageTimelineProps {
  stageInputs: StageInput[];
  stageOutputs: StageOutput[];
  replanEvents: ReplanEvent[];
  onViewInput?: (stage: string) => void;
  onViewOutput?: (stage: string) => void;
}

const stageLabels: Record<string, string> = {
  route_plan: 'ROUTE+PLAN',
  validate: 'VALIDATE',
  execute: 'EXECUTE',
  compose: 'COMPOSE',
  present: 'PRESENT',
};

export function StageTimeline({
  stageInputs,
  stageOutputs,
  replanEvents,
  onViewInput,
  onViewOutput,
}: StageTimelineProps) {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set());
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  const toggleExpand = (stage: string) => {
    const newExpanded = new Set(expandedStages);
    if (newExpanded.has(stage)) {
      newExpanded.delete(stage);
    } else {
      newExpanded.add(stage);
    }
    setExpandedStages(newExpanded);
  };

  // Stage와 Replan을 시간순으로 인터리브
  const timelineItems = buildTimelineItems(stageOutputs, replanEvents);

  return (
    <div className="space-y-2">
      {timelineItems.map((item, idx) => (
        <React.Fragment key={item.id}>
          {item.type === 'stage' && (
            <StageCard
              input={stageInputs.find(i => i.stage === item.stage)!}
              output={item.output}
              isExpanded={expandedStages.has(item.stage)}
              isSelected={selectedStage === item.stage}
              onToggle={() => toggleExpand(item.stage)}
              onSelect={() => setSelectedStage(item.stage)}
              onViewInput={() => onViewInput?.(item.stage)}
              onViewOutput={() => onViewOutput?.(item.stage)}
            />
          )}
          {item.type === 'replan' && (
            <ReplanCard event={item.event} />
          )}
          {/* Connector line */}
          {idx < timelineItems.length - 1 && (
            <div className="flex justify-center">
              <div className="w-0.5 h-4 bg-slate-700" />
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

interface StageCardProps {
  input: StageInput;
  output: StageOutput;
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: () => void;
  onViewInput: () => void;
  onViewOutput: () => void;
}

function StageCard({
  input,
  output,
  isExpanded,
  isSelected,
  onToggle,
  onSelect,
  onViewInput,
  onViewOutput,
}: StageCardProps) {
  const diag = output.diagnostics;
  const StatusIcon = diag.status === 'ok' ? Check : diag.status === 'warning' ? AlertTriangle : X;
  const statusColor = diag.status === 'ok'
    ? 'text-emerald-400'
    : diag.status === 'warning'
    ? 'text-amber-400'
    : 'text-rose-400';

  return (
    <div
      className={`border rounded-lg ${isSelected ? 'border-sky-500' : 'border-slate-700'} bg-slate-800/50`}
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-700/30"
        onClick={onToggle}
      >
        <button className="text-slate-400">
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>

        <div className="flex-1 flex items-center gap-3">
          <span className="font-mono text-sm font-semibold">
            {stageLabels[output.stage] || output.stage}
          </span>

          <span className="text-sm text-slate-400">
            {output.duration_ms}ms
          </span>

          <StatusIcon size={16} className={statusColor} />
        </div>

        {/* Quick Stats */}
        <div className="flex items-center gap-4 text-xs text-slate-400">
          {diag.counts.rows !== undefined && (
            <span>Rows: {diag.counts.rows}</span>
          )}
          {diag.counts.blocks !== undefined && (
            <span>Blocks: {diag.counts.blocks}</span>
          )}
          {output.references.length > 0 && (
            <span>Refs: {output.references.length}</span>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-slate-700">
          {/* Assets */}
          <div className="mt-4">
            <h4 className="text-xs font-semibold text-slate-500 mb-2">Applied Assets</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(input.applied_assets).map(([type, id]) => (
                <span
                  key={type}
                  className="px-2 py-1 text-xs rounded bg-slate-700 text-slate-300"
                >
                  {type}: {id}
                </span>
              ))}
            </div>
          </div>

          {/* Diagnostics */}
          {(diag.warnings.length > 0 || diag.errors.length > 0) && (
            <div className="space-y-2">
              {diag.warnings.map((w, i) => (
                <div key={i} className="text-xs text-amber-400 flex items-center gap-2">
                  <AlertTriangle size={12} />
                  {w}
                </div>
              ))}
              {diag.errors.map((e, i) => (
                <div key={i} className="text-xs text-rose-400 flex items-center gap-2">
                  <X size={12} />
                  {e}
                </div>
              ))}
            </div>
          )}

          {/* View Buttons */}
          <div className="flex gap-2">
            <button
              onClick={onViewInput}
              className="px-3 py-1.5 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
            >
              View Input
            </button>
            <button
              onClick={onViewOutput}
              className="px-3 py-1.5 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
            >
              View Output
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

interface ReplanCardProps {
  event: ReplanEvent;
}

function ReplanCard({ event }: ReplanCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-amber-600/50 rounded-lg bg-amber-900/20 px-4 py-3">
      <div
        className="flex items-center gap-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <RefreshCw size={16} className="text-amber-400" />
        <span className="font-semibold text-amber-400">REPLAN #{event.attempt}</span>
        <span className="text-sm text-slate-400">
          Trigger: {event.trigger}
        </span>
        <span className="text-sm text-slate-400">
          Scope: {event.scope}
        </span>
        <span className="text-sm text-slate-400">
          Decision: {event.decision}
        </span>
      </div>

      {expanded && event.patch && (
        <div className="mt-3 p-3 bg-slate-800 rounded text-xs font-mono">
          <pre>{JSON.stringify(event.patch, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

interface TimelineItem {
  id: string;
  type: 'stage' | 'replan';
  stage?: string;
  output?: StageOutput;
  event?: ReplanEvent;
  timestamp?: number;
}

function buildTimelineItems(
  outputs: StageOutput[],
  replans: ReplanEvent[]
): TimelineItem[] {
  const items: TimelineItem[] = [];

  // Stage 순서대로 추가
  const stageOrder = ['route_plan', 'validate', 'execute', 'compose', 'present'];
  let replanIdx = 0;

  for (const stage of stageOrder) {
    const output = outputs.find(o => o.stage === stage);
    if (!output) continue;

    items.push({
      id: `stage-${stage}`,
      type: 'stage',
      stage,
      output,
    });

    // 해당 stage 후의 replan 이벤트 추가
    while (replanIdx < replans.length) {
      const replan = replans[replanIdx];
      if (replan.scope.toLowerCase() === stage) {
        items.push({
          id: `replan-${replan.event_id}`,
          type: 'replan',
          event: replan,
        });
        replanIdx++;
      } else {
        break;
      }
    }
  }

  return items;
}

export default StageTimeline;
```

---

## 1.9 Frontend: OPS 페이지 수정

### 파일: `apps/web/src/app/ops/page.tsx` (수정)

기존 파일의 Answer Panel 영역에 다음을 추가:

```tsx
// Import 추가
import { OpsSummaryStrip } from '@/components/ops/OpsSummaryStrip';
import { StageTimeline } from '@/components/ops/StageTimeline';

// ... 기존 코드 ...

// Answer 표시 영역에서 (대략 라인 600-800 근처)
// 기존의 meta/trace JSON 표시 대신 새 컴포넌트 사용:

{currentAnswer && (
  <div className="space-y-4">
    {/* Summary Strip */}
    <OpsSummaryStrip
      route={currentAnswer.trace?.route || 'orch'}
      planMode={currentAnswer.trace?.plan_validated?.mode}
      toolCount={currentAnswer.trace?.tool_calls?.length || 0}
      replanCount={currentAnswer.trace?.replan_events?.length || 0}
      warningCount={
        currentAnswer.trace?.stage_outputs?.filter(
          (s: any) => s.diagnostics.status === 'warning'
        ).length || 0
      }
      referenceCount={currentAnswer.trace?.references?.length || 0}
      durationMs={currentAnswer.meta?.timing_ms || 0}
      testMode={currentAnswer.trace?.test_mode}
    />

    {/* Tab Navigation */}
    <div className="flex border-b border-slate-700">
      <TabButton
        active={activeTab === 'timeline'}
        onClick={() => setActiveTab('timeline')}
      >
        Timeline
      </TabButton>
      <TabButton
        active={activeTab === 'blocks'}
        onClick={() => setActiveTab('blocks')}
      >
        Blocks
      </TabButton>
      <TabButton
        active={activeTab === 'actions'}
        onClick={() => setActiveTab('actions')}
      >
        Actions
      </TabButton>
      <TabButton
        active={activeTab === 'raw'}
        onClick={() => setActiveTab('raw')}
      >
        Raw
      </TabButton>
    </div>

    {/* Tab Content */}
    {activeTab === 'timeline' && currentAnswer.trace?.stage_outputs && (
      <StageTimeline
        stageInputs={currentAnswer.trace.stage_inputs || []}
        stageOutputs={currentAnswer.trace.stage_outputs || []}
        replanEvents={currentAnswer.trace.replan_events || []}
        onViewInput={(stage) => setInspectModal({ type: 'input', stage })}
        onViewOutput={(stage) => setInspectModal({ type: 'output', stage })}
      />
    )}

    {activeTab === 'blocks' && (
      <BlockRenderer
        blocks={currentAnswer.blocks}
        traceId={currentAnswer.trace?.trace_id}
      />
    )}

    {activeTab === 'actions' && currentAnswer.next_actions && (
      <NextActionsPanel actions={currentAnswer.next_actions} />
    )}

    {activeTab === 'raw' && (
      <pre className="p-4 bg-slate-900 rounded-lg text-xs overflow-auto max-h-96">
        {JSON.stringify(currentAnswer.trace, null, 2)}
      </pre>
    )}
  </div>
)}
```

---

# Phase 2 상세 구현 명세

## 2.1 Source Asset 모델

### 파일: `apps/api/app/modules/asset_registry/models.py` (수정)

```python
# TbAssetRegistry 클래스에 Source 관련 필드 추가

class TbAssetRegistry(SQLModel, table=True):
    __tablename__ = "tb_asset_registry"

    # ... 기존 필드들 ...

    # === Source Asset 필드 (신규) ===
    source_engine: Optional[str] = Field(
        default=None,
        description="Source engine: postgres|timescale|neo4j|vector|http_api"
    )
    source_connection: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Connection config (host, port, credentials...)"
    )
    source_permissions: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Permission settings (read_only, allowed_schemas...)"
    )
    source_health_check: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Health check config"
    )
    source_last_health_check: Optional[datetime] = Field(default=None)
    source_health_status: Optional[str] = Field(default=None)  # ok|warn|error

    # === SchemaCatalog Asset 필드 (신규) ===
    catalog_source_id: Optional[str] = Field(
        default=None,
        description="연결된 Source Asset ID"
    )
    catalog_entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
        description="Entity 목록"
    )
    catalog_auto_sync: bool = Field(default=False)
    catalog_sync_schedule: Optional[str] = Field(default=None)
    catalog_last_synced_at: Optional[datetime] = Field(default=None)

    # === ResolverConfig Asset 필드 (신규) ===
    resolver_alias_mappings: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB)
    )
    resolver_pattern_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB)
    )
    resolver_ambiguity_policy: str = Field(default="ask_user")
    resolver_max_candidates: int = Field(default=5)
    resolver_cache_ttl_seconds: int = Field(default=3600)
```

---

## 2.2 Control Loop Runtime

### 파일: `apps/api/app/modules/ops/services/control_loop.py` (신규 생성)

전체 구현은 메인 문서의 Section 5.4 참조. 핵심 메서드:

```python
class ControlLoopRuntime:
    async def run(self, plan_output: PlanOutput, context: ExecutionContext) -> Dict[str, Any]:
        """Control Loop 적용하여 파이프라인 실행"""
        # 구현 내용은 메인 문서 참조

    def _detect_trigger(self, stage_outputs: List[StageOutput]) -> Optional[ReplanTrigger]:
        """Stage 출력에서 Replan 트리거 감지"""
        if not stage_outputs:
            return None

        last = stage_outputs[-1]
        diag = last.diagnostics

        if diag.status == "error":
            for err in diag.errors:
                if "timeout" in err.lower() or "retry" in err.lower():
                    return ReplanTrigger.TOOL_ERROR_RETRYABLE
            return ReplanTrigger.TOOL_ERROR_FATAL

        if diag.empty_flags.get("result_empty"):
            return ReplanTrigger.EMPTY_RESULT

        if diag.counts.get("references", 0) == 0 and last.stage == "compose":
            return ReplanTrigger.LOW_EVIDENCE

        return None
```

---

# Phase 3 상세 구현 명세

## 3.1 Inspector Stage Pipeline 시각화

### 파일: `apps/web/src/components/admin/inspector/StagePipelineView.tsx` (신규 생성)

```tsx
/**
 * Stage Pipeline Visualization for Inspector
 */

import React, { useState, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';

interface StagePipelineViewProps {
  stageInputs: any[];
  stageOutputs: any[];
  replanEvents: any[];
  onStageSelect: (stage: string) => void;
  selectedStage?: string;
}

export function StagePipelineView({
  stageInputs,
  stageOutputs,
  replanEvents,
  onStageSelect,
  selectedStage,
}: StagePipelineViewProps) {
  const { nodes, edges } = useMemo(() => {
    return buildFlowGraph(stageOutputs, replanEvents);
  }, [stageOutputs, replanEvents]);

  return (
    <div className="h-64 bg-slate-900 rounded-lg border border-slate-700">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) => onStageSelect(node.id)}
        fitView
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Background color="#334155" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function buildFlowGraph(outputs: any[], replans: any[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const stageOrder = ['route_plan', 'validate', 'execute', 'compose', 'present'];
  let xPos = 0;
  const yPos = 100;
  const spacing = 180;

  // Create stage nodes
  stageOrder.forEach((stage, idx) => {
    const output = outputs.find(o => o.stage === stage);
    if (!output) return;

    const diag = output.diagnostics;
    const statusColor = diag.status === 'ok'
      ? '#10b981'
      : diag.status === 'warning'
      ? '#f59e0b'
      : '#ef4444';

    nodes.push({
      id: stage,
      position: { x: xPos, y: yPos },
      data: {
        label: (
          <div className="text-center">
            <div className="font-bold">{stage.toUpperCase()}</div>
            <div className="text-xs">{output.duration_ms}ms</div>
          </div>
        ),
      },
      style: {
        background: '#1e293b',
        border: `2px solid ${statusColor}`,
        borderRadius: '8px',
        padding: '10px',
        color: '#e2e8f0',
      },
    });

    // Edge to next stage
    if (idx < stageOrder.length - 1) {
      const nextStage = stageOrder[idx + 1];
      if (outputs.find(o => o.stage === nextStage)) {
        edges.push({
          id: `${stage}-${nextStage}`,
          source: stage,
          target: nextStage,
          animated: true,
          style: { stroke: '#64748b' },
        });
      }
    }

    xPos += spacing;
  });

  // Add replan nodes
  replans.forEach((replan, idx) => {
    const replanId = `replan-${idx}`;
    const scopeStage = replan.scope.toLowerCase();
    const stageIdx = stageOrder.indexOf(scopeStage);

    if (stageIdx >= 0) {
      nodes.push({
        id: replanId,
        position: { x: stageIdx * spacing, y: yPos + 80 },
        data: {
          label: (
            <div className="text-center text-xs">
              <div className="font-bold text-amber-400">REPLAN #{replan.attempt}</div>
              <div>{replan.trigger}</div>
            </div>
          ),
        },
        style: {
          background: '#451a03',
          border: '1px solid #f59e0b',
          borderRadius: '4px',
          padding: '6px',
          color: '#fcd34d',
        },
      });

      // Edge from stage to replan
      edges.push({
        id: `${scopeStage}-${replanId}`,
        source: scopeStage,
        target: replanId,
        style: { stroke: '#f59e0b', strokeDasharray: '5,5' },
      });
    }
  });

  return { nodes, edges };
}

export default StagePipelineView;
```

---

## 3.2 Asset Override Test UI

### 파일: `apps/web/src/components/ops/AssetOverrideDrawer.tsx` (신규 생성)

```tsx
/**
 * Asset Override Drawer - 테스트 모드에서 Asset 교체
 */

import React, { useState, useEffect } from 'react';
import { X, Play } from 'lucide-react';

interface Asset {
  asset_id: string;
  name: string;
  asset_type: string;
  version: number;
  status: string;
}

interface AssetOverrideDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onRunTest: (overrides: Record<string, string>) => void;
  currentAssets: Record<string, string>;
}

const STAGES = ['route_plan', 'validate', 'execute', 'compose', 'present'];
const STAGE_ASSETS: Record<string, string[]> = {
  route_plan: ['prompt', 'policy', 'schema_catalog'],
  validate: ['policy'],
  execute: ['query', 'source', 'mapping'],
  compose: ['mapping'],
  present: ['screen'],
};

export function AssetOverrideDrawer({
  isOpen,
  onClose,
  onRunTest,
  currentAssets,
}: AssetOverrideDrawerProps) {
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [availableAssets, setAvailableAssets] = useState<Record<string, Asset[]>>({});
  const [loading, setLoading] = useState(false);

  // Load available assets
  useEffect(() => {
    if (isOpen) {
      loadAvailableAssets();
    }
  }, [isOpen]);

  const loadAvailableAssets = async () => {
    setLoading(true);
    try {
      const assetTypes = ['prompt', 'policy', 'query', 'mapping', 'screen', 'source', 'schema_catalog'];
      const results: Record<string, Asset[]> = {};

      for (const type of assetTypes) {
        const res = await fetch(`/api/asset-registry/assets?asset_type=${type}&status=published`);
        const data = await res.json();
        results[type] = data.data || [];
      }

      setAvailableAssets(results);
    } catch (err) {
      console.error('Failed to load assets:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOverrideChange = (stage: string, assetType: string, assetId: string) => {
    const key = `${stage}:${assetType}`;
    setOverrides(prev => ({
      ...prev,
      [key]: assetId,
    }));
  };

  const handleRunTest = () => {
    onRunTest(overrides);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-slate-900 border-l border-slate-700 shadow-xl z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h3 className="font-semibold">Test Mode - Asset Override</h3>
        <button onClick={onClose} className="p-1 hover:bg-slate-700 rounded">
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 overflow-y-auto h-[calc(100%-120px)]">
        {loading ? (
          <div className="text-center py-8 text-slate-400">Loading assets...</div>
        ) : (
          <div className="space-y-6">
            {STAGES.map(stage => (
              <div key={stage} className="space-y-3">
                <h4 className="font-semibold text-slate-300 text-sm uppercase">
                  {stage.replace('_', '+')}
                </h4>

                {STAGE_ASSETS[stage].map(assetType => {
                  const assets = availableAssets[assetType] || [];
                  const currentValue = currentAssets[`${stage}:${assetType}`] || '';
                  const overrideValue = overrides[`${stage}:${assetType}`];

                  return (
                    <div key={assetType} className="space-y-1">
                      <label className="text-xs text-slate-500">{assetType}</label>
                      <select
                        value={overrideValue || currentValue}
                        onChange={(e) => handleOverrideChange(stage, assetType, e.target.value)}
                        className={`w-full px-3 py-2 rounded bg-slate-800 border text-sm
                          ${overrideValue ? 'border-amber-500' : 'border-slate-700'}`}
                      >
                        <option value="">-- Current --</option>
                        {assets.map(asset => (
                          <option key={asset.asset_id} value={`${asset.asset_id}:${asset.version}`}>
                            {asset.name} (v{asset.version})
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700 bg-slate-900">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-slate-400">
            {Object.keys(overrides).length} override(s) selected
          </span>
          <button
            onClick={() => setOverrides({})}
            className="text-sm text-slate-400 hover:text-slate-200"
          >
            Clear All
          </button>
        </div>

        <button
          onClick={handleRunTest}
          disabled={Object.keys(overrides).length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded
            bg-amber-600 hover:bg-amber-500 disabled:bg-slate-700 disabled:text-slate-500
            font-semibold transition-colors"
        >
          <Play size={16} />
          Run Test with Overrides
        </button>
      </div>
    </div>
  );
}

export default AssetOverrideDrawer;
```

---

# 테스트 명세

## Unit Tests

### Backend Tests

#### `apps/api/tests/test_plan_output.py`

```python
"""PlanOutput 스키마 테스트"""

import pytest
from app.modules.ops.services.ci.planner.plan_output import (
    PlanOutput, PlanOutputKind, DirectAnswerPayload, RejectPayload
)


class TestPlanOutput:
    def test_direct_answer_valid(self):
        output = PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct=DirectAnswerPayload(
                answer_text="안녕하세요!",
                confidence=0.95
            )
        )
        assert output.is_direct()
        assert not output.is_orchestration()
        assert output.get_route_label() == "direct"

    def test_plan_valid(self):
        from app.modules.ops.services.ci.planner.plan_schema import Plan, Intent
        output = PlanOutput(
            kind=PlanOutputKind.PLAN,
            plan=Plan(intent=Intent.LOOKUP, identifiers=["GT-01"])
        )
        assert output.is_orchestration()
        assert output.get_route_label() == "orch"

    def test_reject_valid(self):
        output = PlanOutput(
            kind=PlanOutputKind.REJECT,
            reject=RejectPayload(reason="삭제 불가")
        )
        assert output.is_reject()
        assert output.get_route_label() == "reject"

    def test_inconsistent_kind_direct(self):
        with pytest.raises(ValueError, match="kind=direct requires direct payload"):
            PlanOutput(kind=PlanOutputKind.DIRECT)

    def test_inconsistent_kind_plan(self):
        with pytest.raises(ValueError, match="kind=plan requires plan payload"):
            PlanOutput(kind=PlanOutputKind.PLAN)


class TestDirectAnswerPayload:
    def test_valid_sources(self):
        for source in ["knowledge", "cache", "fallback"]:
            payload = DirectAnswerPayload(answer_text="test", source=source)
            assert payload.source == source

    def test_invalid_source(self):
        with pytest.raises(ValueError):
            DirectAnswerPayload(answer_text="test", source="invalid")

    def test_confidence_bounds(self):
        with pytest.raises(ValueError):
            DirectAnswerPayload(answer_text="test", confidence=1.5)
```

#### `apps/api/tests/test_stage_executor.py`

```python
"""Stage Executor 테스트"""

import pytest
from unittest.mock import AsyncMock, patch
from app.modules.ops.services.stage_executor import StageExecutor, ExecutionContext
from app.modules.ops.services.ci.planner.plan_output import (
    PlanOutput, PlanOutputKind, DirectAnswerPayload
)


@pytest.fixture
def context():
    return ExecutionContext(
        tenant_id="test",
        question="GT-01 상태",
        trace_id="test-trace-123"
    )


class TestStageExecutor:
    @pytest.mark.asyncio
    async def test_direct_answer_skips_execute(self, context):
        plan_output = PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct=DirectAnswerPayload(answer_text="안녕하세요!")
        )

        executor = StageExecutor(context)
        result = await executor.run_all_stages(plan_output)

        assert result["route"] == "direct"
        # Execute stage should be skipped
        stages_run = [so["stage"] for so in result["stage_outputs"]]
        assert "execute" not in stages_run
        assert "compose" not in stages_run

    @pytest.mark.asyncio
    async def test_plan_runs_all_stages(self, context):
        from app.modules.ops.services.ci.planner.plan_schema import Plan, Intent

        plan_output = PlanOutput(
            kind=PlanOutputKind.PLAN,
            plan=Plan(intent=Intent.LOOKUP, identifiers=["GT-01"])
        )

        with patch.object(StageExecutor, '_execute_execute', new_callable=AsyncMock) as mock:
            mock.return_value = {"rows": [{"id": 1}], "blocks": [], "references": []}

            executor = StageExecutor(context)
            result = await executor.run_all_stages(plan_output)

        assert result["route"] == "orch"
        stages_run = [so["stage"] for so in result["stage_outputs"]]
        assert "validate" in stages_run
        assert "execute" in stages_run
        assert "compose" in stages_run

    @pytest.mark.asyncio
    async def test_empty_result_triggers_replan(self, context):
        from app.modules.ops.services.ci.planner.plan_schema import Plan, Intent

        plan_output = PlanOutput(
            kind=PlanOutputKind.PLAN,
            plan=Plan(intent=Intent.LOOKUP, identifiers=["UNKNOWN"])
        )

        with patch.object(StageExecutor, '_execute_execute', new_callable=AsyncMock) as mock:
            mock.return_value = {"rows": [], "blocks": [], "references": []}

            executor = StageExecutor(context)
            await executor.run_all_stages(plan_output)

            trigger = executor.get_replan_trigger()
            assert trigger == "EMPTY_RESULT"
```

### Frontend Tests

#### `apps/web/src/components/ops/__tests__/OpsSummaryStrip.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import { OpsSummaryStrip } from '../OpsSummaryStrip';

describe('OpsSummaryStrip', () => {
  it('renders route badge correctly', () => {
    render(
      <OpsSummaryStrip
        route="direct"
        toolCount={0}
        replanCount={0}
        warningCount={0}
        referenceCount={0}
        durationMs={100}
      />
    );

    expect(screen.getByText('DIRECT')).toBeInTheDocument();
  });

  it('shows test mode indicator', () => {
    render(
      <OpsSummaryStrip
        route="orch"
        toolCount={3}
        replanCount={1}
        warningCount={0}
        referenceCount={5}
        durationMs={1200}
        testMode={true}
      />
    );

    expect(screen.getByText('TEST')).toBeInTheDocument();
  });

  it('highlights replans when count > 0', () => {
    render(
      <OpsSummaryStrip
        route="orch"
        toolCount={2}
        replanCount={2}
        warningCount={0}
        referenceCount={3}
        durationMs={800}
      />
    );

    const replansValue = screen.getByText('2');
    expect(replansValue).toHaveClass('text-sky-400');
  });
});
```

---

## Integration Tests

### E2E Flow Test

```python
# apps/api/tests/integration/test_ops_flow.py

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_direct_answer_flow(client: AsyncClient):
    """Direct answer 전체 흐름 테스트"""
    response = await client.post("/ops/ci/ask", json={
        "question": "안녕하세요"
    })

    assert response.status_code == 200
    data = response.json()["data"]

    # Route should be direct
    assert data["trace"]["route"] == "direct"

    # Stage outputs should exist
    assert len(data["trace"]["stage_outputs"]) >= 2

    # No tool calls for direct answer
    assert len(data["trace"]["tool_calls"]) == 0


@pytest.mark.asyncio
async def test_orchestration_flow(client: AsyncClient):
    """Orchestration 전체 흐름 테스트"""
    response = await client.post("/ops/ci/ask", json={
        "question": "GT-01 상태 알려줘"
    })

    assert response.status_code == 200
    data = response.json()["data"]

    # Route should be orch
    assert data["trace"]["route"] == "orch"

    # All stages should have outputs
    stages = [so["stage"] for so in data["trace"]["stage_outputs"]]
    assert "route_plan" in stages
    assert "validate" in stages
    assert "execute" in stages
    assert "compose" in stages


@pytest.mark.asyncio
async def test_reject_flow(client: AsyncClient):
    """Reject 전체 흐름 테스트"""
    response = await client.post("/ops/ci/ask", json={
        "question": "모든 데이터 삭제해줘"
    })

    assert response.status_code == 200
    data = response.json()["data"]

    # Route should be reject
    assert data["trace"]["route"] == "reject"

    # Should have reject message in blocks
    assert any("처리할 수 없습니다" in str(block) for block in data["blocks"])
```

---

> **문서 버전**: 1.0
> **작성일**: 2026-01-22
> **용도**: AI 에이전트 개발 가이드
