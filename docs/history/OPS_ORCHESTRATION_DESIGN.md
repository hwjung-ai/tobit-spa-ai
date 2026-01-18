# OPS 오케스트레이션 시스템 상세 설계안

**작성일**: 2026-01-18
**상태**: 설계 검토 대기
**우선순위**: P0 (핵심 기능)

---

## 📋 목차

1. [비전](#비전)
2. [현재 상태](#현재-상태)
3. [설계 원칙](#설계-원칙)
4. [아키텍처 개선](#아키텍처-개선)
5. [구현 계획](#구현-계획)
6. [사용자 경험 설계](#사용자-경험-설계)
7. [향후 확장성](#향후-확장성)
8. [구현 로드맵](#구현-로드맵)

---

## 🎯 비전

### 목표
사용자가 자신이 보유한 **모든 데이터**를 자연스럽게 질의할 수 있는 통합 오케스트레이션 엔진 구축

### 핵심 가치
- **통합성**: CI, 메트릭, 이벤트, 문서 등 모든 데이터 소스를 하나의 질문으로 조회
- **확장성**: 새로운 데이터 소스를 쉽게 추가할 수 있는 플러그인 아키텍처
- **사용성**: 자연스러운 한국어 질문으로 복잡한 분석 수행
- **신뢰성**: 부분 실패 시에도 사용 가능한 결과 제공

### 진화 경로
```
Phase 1 (현재): CI 중심 오케스트레이션
  └─ CI 정보, 메트릭, 이벤트, CEP 규칙

Phase 2 (3개월): 문서 검색 통합
  └─ 위 + 운영 설명서, 가이드, 매뉴얼

Phase 3 (6개월): 외부 시스템 연계
  └─ 위 + TIM+ 메트릭, 모니터링 데이터, 제3자 API

Phase 4 (12개월): AI 기반 분석
  └─ 위 + 근본 원인 분석, 이상 징후 검출, 자동 해결 제안
```

---

## 📊 현재 상태

### 기존 시스템 (✅ 작동 중)
- **Planner**: 한국어 질문 → 구조화된 Plan (intent/view/scope)
- **Validator**: 정책 기반 깊이/관계 제한
- **Orchestrator**: Plan 실행, 도구 조율
- **Tools**: CI(Postgres), Graph(Neo4j), Metric, History, CEP
- **UI**: 블록 기반 렌더링 (text, table, network, chart, path)

### 갭 분석
| 항목 | 현황 | 문제 |
|------|------|------|
| **사용성** | 복잡한 쿼리 필요 | 직관적이지 않은 사용자 경험 |
| **문서 통합** | 미구현 | 운영 정보 접근 불가 |
| **오류 처리** | 부분적 | 사용자 친화적 오류 메시지 부족 |
| **캐싱** | 없음 | 성능 저하 |
| **다중 의도** | 부분 지원 | 복합 질문 처리 미흡 |
| **UX 피드백** | 제한적 | 사용자 가이드 부족 |

---

## 🏛️ 설계 원칙

### 1. **플러그인 아키텍처**
```
Core Orchestration Engine
    │
    ├─ Tool Interface (abstract)
    │   ├─ CI Tool (Postgres)
    │   ├─ Graph Tool (Neo4j)
    │   ├─ Metric Tool (Postgres)
    │   ├─ History Tool (Postgres)
    │   ├─ CEP Tool (Rule Engine)
    │   ├─ Document Tool (NEW)
    │   ├─ Compliance Tool (TBD)
    │   └─ ... custom tools
    │
    ├─ Data Source Registry
    │   ├─ Postgres
    │   ├─ Neo4j
    │   ├─ Search Backend (Elasticsearch/Milvus)
    │   ├─ External APIs (TIM+)
    │   └─ ... custom backends
    │
    └─ Block Type Registry
        ├─ text, table, network, chart
        ├─ path, timeline, heatmap (NEW)
        └─ ... custom blocks
```

### 2. **사용자 중심 설계**
- **명확한 의도 파악**: "뭐야", "보여줘", "분석해줘", "비교해줘" 등 자연스러운 표현
- **점진적 공개**: 복잡한 결과를 단계별로 보여주기
- **컨텍스트 유지**: 이전 질문을 기반으로 다음 질문 추천
- **오류 복구**: 실패 시 대체 데이터 제시, 재시도 옵션

### 3. **신뢰성과 투명성**
- **부분 실패 허용**: 일부 도구 실패해도 다른 결과 제시
- **실행 추적**: 모든 단계를 trace에 기록
- **근거 제시**: 결과 근처에 데이터 출처, 신뢰도 표시
- **사용자 피드백**: "도움이 되셨나요?" 를 통한 개선

### 4. **확장 가능성**
- **데이터 소스**: 새로운 backend 추가 가능
- **도구**: 새로운 Tool 추가 가능
- **출력 형식**: 새로운 Block 타입 추가 가능
- **정책**: YAML 기반 선언형 정책 (코드 변경 불필요)

---

## 🔧 아키텍처 개선

### 개선 1: Tool Interface 통일화

```python
# apps/api/app/modules/ops/services/ci/tools/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ToolContext:
    """Tool 실행 컨텍스트"""
    tenant_id: str
    trace_id: str
    user_id: str
    question: str
    plan: "Plan"
    ci_ids: List[str]  # 현재 필터링된 CI IDs
    meta: Dict[str, Any]  # 도구 간 데이터 공유

@dataclass
class ToolResult:
    """Tool 실행 결과"""
    type: str  # "ci", "graph", "metric", "document", etc.
    status: str  # "ok", "empty", "error", "partial"
    rows: List[Dict[str, Any]]
    meta: Dict[str, Any]  # {row_count, columns, ci_count, truncated, ...}
    trace: Dict[str, Any]  # 실행 로그
    error: Optional[str] = None

class BaseTool(ABC):
    """모든 Tool의 기본 클래스"""

    def __init__(self, data_source):
        self.data_source = data_source

    @abstractmethod
    async def execute(
        self,
        context: ToolContext,
        **kwargs
    ) -> ToolResult:
        """Tool 실행"""
        pass

    def format_error(self, error: Exception) -> str:
        """사용자 친화적 에러 메시지"""
        pass

    def should_execute(self, plan: "Plan") -> bool:
        """이 도구를 실행할지 판단"""
        pass

# tools/ci_tool.py, graph_tool.py, metric_tool.py, ... 모두 이 인터페이스 구현
```

### 개선 2: Tool Registry와 동적 로딩

```python
# apps/api/app/modules/ops/services/ci/tools/__init__.py

from enum import Enum
from typing import Dict, Type

class ToolType(str, Enum):
    """지원하는 Tool 타입"""
    CI = "ci"
    GRAPH = "graph"
    METRIC = "metric"
    HISTORY = "history"
    CEP = "cep"
    DOCUMENT = "document"
    COMPLIANCE = "compliance"
    # 추가 가능

class ToolRegistry:
    """Tool 동적 로딩 및 관리"""

    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}

    def register(self, tool_type: ToolType, tool_class: Type[BaseTool]):
        """Tool 등록"""
        self._tools[tool_type.value] = tool_class

    def get_tool(self, tool_type: ToolType) -> BaseTool:
        """Tool 인스턴스 조회 (싱글톤)"""
        key = tool_type.value
        if key not in self._instances:
            tool_class = self._tools[key]
            self._instances[key] = tool_class()
        return self._instances[key]

    def list_available_tools(self) -> List[str]:
        """사용 가능한 Tool 목록"""
        return list(self._tools.keys())

# 전역 레지스트리
TOOL_REGISTRY = ToolRegistry()

# 모듈 로드 시 자동 등록
from .tools import ci, graph, metric, history, cep, document

TOOL_REGISTRY.register(ToolType.CI, ci.CITool)
TOOL_REGISTRY.register(ToolType.GRAPH, graph.GraphTool)
TOOL_REGISTRY.register(ToolType.METRIC, metric.MetricTool)
TOOL_REGISTRY.register(ToolType.HISTORY, history.HistoryTool)
TOOL_REGISTRY.register(ToolType.CEP, cep.CEPTool)
TOOL_REGISTRY.register(ToolType.DOCUMENT, document.DocumentTool)  # NEW
```

### 개선 3: Plan 확장 (문서 + 추가 데이터 소스)

```python
# apps/api/app/modules/ops/services/ci/planner/plan_schema.py

from dataclasses import dataclass, field
from typing import Optional, List, Literal

@dataclass
class DocumentSpec:
    """문서 검색 스펙"""
    enabled: bool = False
    query: str | None = None
    scope: Literal["ci", "graph", "global"] = "ci"
    limit: int = 20
    filter_by_ci: bool = True  # scope=ci 시 CI로 필터링

@dataclass
class ComplianceSpec:
    """준수성 검증 스펙 (향후)"""
    enabled: bool = False
    rule_id: str | None = None
    scope: Literal["ci", "graph"] = "ci"

@dataclass
class ExternalSpec:
    """외부 시스템 연계 스펙 (향후)"""
    enabled: bool = False
    system: str | None = None  # "tim+", "prometheus", ...
    query: str | None = None

@dataclass
class Plan:
    """확장된 Plan"""
    # 기존 필드들
    mode: str
    intent: str
    view: str
    primary: object
    secondary: Optional[object] = None

    # 조회 스펙
    graph: Optional[object] = None
    aggregate: Optional[object] = None
    metric: Optional[object] = None
    history: Optional[object] = None
    cep: Optional[object] = None
    list: Optional[object] = None

    # 신규 스펙 (확장 가능)
    document: Optional[DocumentSpec] = None
    compliance: Optional[ComplianceSpec] = None
    external: Optional[ExternalSpec] = None

    # 메타
    output: object = field(default_factory=dict)
```

### 개선 4: Orchestrator 일반화

```python
# apps/api/app/modules/ops/services/ci/orchestrator/runner.py

class CIOrchestratorRunner:
    """일반화된 오케스트레이션 엔진"""

    async def run(self) -> CiAskResponse:
        # 1. 초기화
        context = self._build_context()
        blocks = []
        trace = {}

        # 2. 도구 선택 (선언형)
        tools_to_execute = self._select_tools()
        # [CI, Graph, Metric, History, CEP, Document] 중 Plan에서 enabled된 것들

        # 3. 실행
        for tool_type in tools_to_execute:
            try:
                tool = TOOL_REGISTRY.get_tool(tool_type)
                result = await tool.execute(context)

                # 블록 생성
                block = self._format_result(result)
                blocks.append(block)

                # Trace 기록
                trace[tool_type.value] = result.trace

                # 컨텍스트 업데이트 (다음 도구용)
                if tool_type == ToolType.GRAPH:
                    context.ci_ids = result.meta.get("ci_ids", [])

            except Exception as e:
                # 부분 실패 처리
                trace[tool_type.value] = {
                    "status": "error",
                    "error": str(e)
                }
                # 사용자 친화적 에러 블록 추가
                blocks.append(text_block(
                    f"{tool_type.value} 조회 실패: {self._humanize_error(e)}"
                ))

        # 4. Next Actions 생성
        next_actions = self._generate_next_actions(blocks, context)

        # 5. 응답 생성
        return CiAskResponse(
            answer=self._summarize(blocks),
            blocks=blocks,
            next_actions=next_actions,
            trace=trace,
            meta={...}
        )

    def _select_tools(self) -> List[ToolType]:
        """Plan 기반 도구 선택"""
        tools = []

        # 기본적으로 CI 조회
        if self.plan.primary:
            tools.append(ToolType.CI)

        # 조건부 도구 선택
        if self.plan.graph:
            tools.append(ToolType.GRAPH)
        if self.plan.metric:
            tools.append(ToolType.METRIC)
        if self.plan.history:
            tools.append(ToolType.HISTORY)
        if self.plan.cep:
            tools.append(ToolType.CEP)
        if self.plan.document:
            tools.append(ToolType.DOCUMENT)
        if self.plan.compliance:
            tools.append(ToolType.COMPLIANCE)

        return tools
```

### 개선 5: 오류 처리 및 사용자 경험

```python
# apps/api/app/modules/ops/services/ci/error_handler.py

class OPSErrorHandler:
    """사용자 친화적 오류 처리"""

    ERROR_MESSAGES = {
        "CI_NOT_FOUND": "시스템을 찾을 수 없습니다. 다른 이름으로 시도해보세요.",
        "GRAPH_TIMEOUT": "관계 조회 시간이 초과했습니다. 범위를 좁혀보세요.",
        "METRIC_MISSING": "메트릭 데이터가 없습니다. 다른 메트릭을 시도해보세요.",
        "TRUNCATED": "결과가 너무 커서 일부만 표시됩니다.",
        "DOCUMENT_NOT_FOUND": "관련 문서를 찾을 수 없습니다.",
        "DATABASE_ERROR": "데이터베이스 조회 오류. 잠시 후 다시 시도하세요.",
    }

    @staticmethod
    def humanize_error(error: Exception) -> str:
        """기술 오류 → 사용자 메시지"""
        error_type = type(error).__name__
        return OPSErrorHandler.ERROR_MESSAGES.get(
            error_type,
            "오류가 발생했습니다. 다시 시도해보세요."
        )

    @staticmethod
    def get_fallback_action(error: Exception) -> str:
        """실패 시 다음 단계 제안"""
        if "TRUNCATED" in str(error):
            return "범위를 좁혀서 다시 시도해보세요."
        elif "NOT_FOUND" in str(error):
            return "다른 검색어로 시도해보세요."
        return "시스템 관리자에게 문의하세요."
```

---

## 👥 사용자 경험 설계

### 1. 자연스러운 질문 이해

#### 지원할 질문 패턴

```
# 정보 조회 (정의, 속성, 상태)
- "sys-erp 뭐야?" → CI detail
- "sys-erp는 뭐하는 거야?" → CI 설명 + 연관 문서
- "sys-erp 상태 어때?" → CI status + 메트릭 + 이벤트

# 관계 탐색
- "sys-erp가 뭘 쓰고 있어?" → USES 관계
- "sys-erp에 의존하는 게 뭐야?" → DEPENDS_ON 역관계
- "sys-erp와 sys-apm이 어떻게 연결돼?" → PATH

# 성능/이벤트 분석
- "sys-erp 요즘 성능 어때?" → 메트릭 + 추이
- "sys-erp에서 최근에 뭐 있었어?" → 이벤트 로그
- "sys-erp 에러 왜 자꾸 나는데?" → 에러 패턴 + 근원 분석

# 복합 분석
- "sys-erp 의존하는 서버들 중에 문제 있는 게 있어?" → 범위 내 상태
- "sys-erp 최근 7일 동안 뭐가 달라졌어?" → diff analysis
- "sys-erp가 느려졌어. 왜 그럴까?" → RCA

# 문서 기반
- "sys-erp 설정 어떻게 해?" → 관련 문서 검색
- "sys-erp와 sys-apm 연동 가이드" → 문서 + 관계

# 범위 기반
- "시스템 전체 상태" → 모든 CI aggregate
- "개발팀 담당 서버들" → 메타데이터 필터링
```

#### 의도 분류 (Planner 개선)

```python
# apps/api/app/modules/ops/services/ci/planner/intent_classifier.py

class IntentClassifier:
    """자연스러운 한국어 의도 분류"""

    INTENT_KEYWORDS = {
        "INFO": {
            "ko": {"뭐야", "뭐하는", "설명", "정보", "상세"},
            "en": {"what is", "describe", "info", "about"}
        },
        "STATUS": {
            "ko": {"어때", "상태", "상황", "괜찮아", "문제"},
            "en": {"status", "how is", "okay", "problem"}
        },
        "TREND": {
            "ko": {"추이", "추세", "변화", "달라졌", "추이"},
            "en": {"trend", "change", "history", "evolution"}
        },
        "COMPARE": {
            "ko": {"비교", "차이", "다른점", "vs", "대비"},
            "en": {"compare", "difference", "vs", "contrast"}
        },
        "GUIDE": {
            "ko": {"어떻게", "설정", "가이드", "방법", "하는법"},
            "en": {"how to", "guide", "setup", "configure"}
        },
        "ANALYZE": {
            "ko": {"왜", "원인", "분석", "뭐때문", "문제점"},
            "en": {"why", "cause", "analyze", "root cause"}
        },
    }

    @staticmethod
    def classify(question: str) -> str:
        """질문 의도 분류"""
        normalized = question.lower()

        for intent, keywords in IntentClassifier.INTENT_KEYWORDS.items():
            all_keywords = keywords.get("ko", set()) | keywords.get("en", set())
            if any(kw in normalized for kw in all_keywords):
                return intent

        return "INFO"  # 기본값

def classify_intent_details(question: str) -> Dict[str, Any]:
    """더 자세한 의도 분석"""
    return {
        "intent": IntentClassifier.classify(question),
        "has_temporal": any(t in question for t in ["최근", "지난", "요즘", "어제", "1시간"]),
        "has_comparison": any(t in question for t in ["비교", "vs", "대비", "차이"]),
        "has_scope": any(t in question for t in ["의존", "영향", "범위", "연관"]),
        "has_document": any(t in question for t in ["설명", "가이드", "문서", "어떻게"]),
    }
```

### 2. 점진적 공개 (Progressive Disclosure)

```python
# 사용자가 한 번에 받는 블록 최소화

# 나쁜 예: 한 번에 모든 정보
blocks = [
    text_block("분석 결과"),
    table_block("CI 상세", 50개 열),
    table_block("관계 네트워크", 1000행),
    table_block("메트릭", 30개 메트릭),
    table_block("이벤트", 200개 행),
]

# 좋은 예: 단계별로 제시
blocks = [
    text_block("sys-erp 상태: 정상"),
    number_block("CPU 사용률", 45, "%"),
    table_block("최근 이벤트 (5개)", 5행, summary=True),

    # Next actions로 드릴다운 제시
    next_actions=[
        {"label": "더 자세히", "action": "expand_metrics"},
        {"label": "최근 7일 추이", "action": "show_trend"},
        {"label": "관련 문서", "action": "search_docs"},
    ]
]
```

### 3. 컨텍스트 추적 및 제안

```python
# apps/api/app/modules/ops/services/ci/context_manager.py

class ContextManager:
    """대화 컨텍스트 추적"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.ci_history: List[str] = []  # 최근 조회한 CI
        self.queries: List[str] = []      # 최근 질문들
        self.current_scope: Optional[List[str]] = None  # 현재 범위

    def suggest_next_questions(self) -> List[str]:
        """다음 질문 제안"""
        if not self.ci_history:
            return []

        last_ci = self.ci_history[-1]
        suggestions = []

        # 관계 탐색
        suggestions.append(f"{last_ci}이 쓰는 시스템은?")

        # 성능 분석
        suggestions.append(f"{last_ci} 최근 성능 어때?")

        # 문서
        suggestions.append(f"{last_ci} 운영 가이드")

        # 이전 CI와의 관계
        if len(self.ci_history) > 1:
            prev_ci = self.ci_history[-2]
            suggestions.append(f"{prev_ci}와 {last_ci} 어떻게 연결돼?")

        return suggestions
```

### 4. 오류 복구 및 피드백

```python
# 오류 발생 시 재시도 옵션 제시

def handle_partial_failure(
    results: Dict[ToolType, ToolResult],
    original_question: str
) -> CiAskResponse:
    """부분 실패 처리"""

    successful_blocks = []
    failed_tools = []

    for tool_type, result in results.items():
        if result.status == "ok":
            successful_blocks.append(format_result(result))
        else:
            failed_tools.append(tool_type.value)

    # 성공한 부분은 표시
    blocks = successful_blocks

    # 실패한 부분에 대한 대안 제시
    if failed_tools:
        blocks.append(text_block(
            f"다음 정보는 조회할 수 없습니다: {', '.join(failed_tools)}\n"
            "다른 방식으로 검색해보세요."
        ))

        # 다시 시도 옵션
        for tool in failed_tools:
            blocks.append(button_block(
                label=f"{tool} 다시 시도",
                action="retry_tool",
                params={"tool_type": tool}
            ))

    # 사용자 피드백
    blocks.append(feedback_block(
        "도움이 되셨나요?",
        options=["매우 유용함", "조금 도움됨", "도움 안 됨"]
    ))

    return CiAskResponse(
        answer=summarize_blocks(blocks),
        blocks=blocks,
        meta={
            "partial_failure": True,
            "failed_tools": failed_tools,
        }
    )
```

---

## 🔮 향후 확장성

### 1. 데이터 소스 추가 (예: 문서 검색)

```python
# Step 1: Document Tool 구현
# apps/api/app/modules/ops/services/ci/tools/document.py

class DocumentTool(BaseTool):
    """문서 검색 도구"""

    async def execute(self, context: ToolContext) -> ToolResult:
        # 1. 질문 파싱
        query = context.plan.document.query
        scope = context.plan.document.scope

        # 2. CI 필터링 (scope 기반)
        ci_filter = None
        if scope == "ci" and context.ci_ids:
            ci_filter = context.ci_ids
        elif scope == "graph" and context.ci_ids:
            # 그래프 범위의 모든 CI 포함
            ci_filter = self._expand_graph_scope(context.ci_ids)

        # 3. 검색 실행
        results = await self._search_documents(
            query=query,
            tenant_id=context.tenant_id,
            ci_filter=ci_filter,
            limit=context.plan.document.limit
        )

        # 4. 결과 반환
        return ToolResult(
            type="document",
            status="ok" if results else "empty",
            rows=[
                {
                    "title": doc["title"],
                    "content_preview": doc["content"][:200],
                    "source": doc["source"],
                    "relevance": doc.get("score", 0.8),
                    "document_id": doc["id"],
                }
                for doc in results
            ],
            meta={
                "row_count": len(results),
                "query": query,
                "scope": scope,
            },
            trace={
                "backend": "elasticsearch",
                "query_time_ms": ...,
            }
        )

    def should_execute(self, plan: "Plan") -> bool:
        return plan.document and plan.document.enabled

# Step 2: Planner 업데이트
# apps/api/app/modules/ops/services/ci/planner/planner_llm.py

def _determine_document_spec(question: str) -> Optional[DocumentSpec]:
    """문서 검색 필요 판단"""
    keywords = {"가이드", "설정", "문서", "how to", "설명서", "어떻게"}

    if any(kw in question for kw in keywords):
        return DocumentSpec(
            enabled=True,
            query=question,
            scope="ci",  # 기본값: CI 범위
        )

    return None

# create_plan()에서 사용
if document_spec := _determine_document_spec(normalized):
    plan.document = document_spec

# Step 3: Orchestrator 업데이트 (자동, 이미 일반화됨)
# tools 추가만으로 자동으로 실행됨

# Step 4: Frontend 블록 렌더러 업데이트
// apps/web/src/components/answer/BlockRenderer.tsx
case "document":
    return <DocumentTable rows={block.rows} />;
```

### 2. 새로운 Block 타입 추가

```python
# apps/api/app/modules/ops/services/ci/blocks.py

# 타임라인 블록 (변화 추적)
class TimelineBlock(TypedDict, total=False):
    type: Literal["timeline"]
    title: str
    events: List[Dict]  # {time, event, details, severity}
    meta: Dict

# 히트맵 블록 (패턴 시각화)
class HeatmapBlock(TypedDict, total=False):
    type: Literal["heatmap"]
    title: str
    matrix: List[List[float]]
    x_labels: List[str]
    y_labels: List[str]
    color_scale: str  # "RdYlGn" (빨강→노랑→초록)

# 산포도 블록 (상관성)
class ScatterBlock(TypedDict, total=False):
    type: Literal["scatter"]
    title: str
    data: List[{"x": float, "y": float, "label": str, "size": int}]
    x_axis: str
    y_axis: str

# 헬퍼 함수
def timeline_block(
    title: str,
    events: List[Dict[str, Any]]
) -> TimelineBlock:
    return {
        "type": "timeline",
        "title": title,
        "events": events,
    }
```

### 3. 정책 확장

```yaml
# apps/api/app/modules/ops/services/ci/policy.yaml (제안)

policies:
  # CI 범위 정책
  ci_scope:
    max_results: 100
    default_limit: 50

  # 그래프 정책
  graph:
    max_depth: 6
    max_nodes: 500
    max_edges: 1000
    views:
      SUMMARY: { depth: 0 }
      COMPOSITION: { depth: 3 }
      DEPENDENCY: { depth: 4 }
      IMPACT: { depth: 4 }
      PATH: { depth: 6 }
      NEIGHBORS: { depth: 1 }

  # 메트릭 정책
  metric:
    max_ci_count: 300
    supported_agg: [min, max, avg, sum, count]
    supported_ranges: [last_1h, last_24h, last_7d, last_30d]

  # 문서 정책
  document:
    max_results: 20
    min_relevance: 0.5
    supported_formats: [md, pdf, doc]
    sources: [confluence, wiki, s3]

  # 캐싱 정책
  cache:
    enabled: true
    ttl:
      ci: 3600
      metric: 600
      document: 1800
    ignore_patterns: []
```

---

## 📋 구현 계획

### Phase 1: 기초 개선 (2주)
- [ ] Tool Interface 통일화 + Registry 구현
- [ ] Plan 스키마 확장 (Document, Compliance, External)
- [ ] Orchestrator 일반화
- [ ] 오류 처리 개선 + UX 메시지

### Phase 2: 문서 검색 통합 (3주)
- [ ] DocumentTool 구현
- [ ] Planner 업데이트 (문서 의도 감지)
- [ ] Frontend 블록 렌더러 추가
- [ ] 테스트 및 검증

### Phase 3: UX 개선 (2주)
- [ ] 자연스러운 의도 분류 개선
- [ ] 점진적 공개 UI 구현
- [ ] 컨텍스트 추적 시스템
- [ ] 다음 질문 제안

### Phase 4: 모니터링 및 피드백 (1주)
- [ ] 사용자 피드백 수집
- [ ] 성능 모니터링
- [ ] 분석 대시보드

---

## 🎯 성공 지표

| 지표 | 목표 | 측정 |
|------|------|------|
| **질문 이해율** | 90% | 올바른 의도 분류 비율 |
| **첫 회 만족도** | 85% | 사용자 피드백 스코어 |
| **부분 실패 복구율** | 80% | 대체 결과 제시 비율 |
| **응답 시간** | < 2초 | P95 응답 시간 |
| **데이터 커버리지** | 95%+ | 실패 도구 없이 결과 제시 |

---

이 설계안은 현재 시스템을 기반으로 하면서도 향후 확장성을 염두에 두었습니다.
다음 단계로 Phase 1 구현을 시작할 준비가 되어 있습니다.
