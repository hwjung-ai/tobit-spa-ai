# OPS 오케스트레이션 구현 로드맵

**작성일**: 2026-01-18
**상태**: 구현 준비 완료
**총 기간**: 8주 (Phase 1-4)

---

## 📅 전체 일정

```
Week 1-2: Phase 1 - 기초 개선
  ├─ Tool Interface 통일화 (3-4일)
  ├─ Tool Registry 구현 (2-3일)
  ├─ Orchestrator 일반화 (3-4일)
  └─ 오류 처리 + UX 개선 (2-3일)

Week 3-5: Phase 2 - 문서 검색 통합
  ├─ DocumentTool 구현 (5-7일)
  ├─ Planner 업데이트 (3-5일)
  ├─ Frontend 블록 추가 (3-4일)
  └─ 테스트 + 검증 (5-7일)

Week 6-7: Phase 3 - UX 개선
  ├─ 의도 분류 개선 (3-4일)
  ├─ 점진적 공개 UI (4-5일)
  ├─ 컨텍스트 시스템 (3-4일)
  └─ 다음 질문 제안 (2-3일)

Week 8: Phase 4 - 모니터링
  ├─ 피드백 수집 시스템 (2-3일)
  ├─ 성능 모니터링 (2-3일)
  └─ 분석 대시보드 (1-2일)
```

---

## 🔄 Phase 1: 기초 개선 (2주)

### 1-1. Tool Interface 통일화

**파일 생성**:
- `apps/api/app/modules/ops/services/ci/tools/base.py`
  - `ToolContext` dataclass
  - `ToolResult` dataclass
  - `BaseTool` abstract class

**기존 파일 수정**:
- `apps/api/app/modules/ops/services/ci/tools/ci.py`
- `apps/api/app/modules/ops/services/ci/tools/graph.py`
- `apps/api/app/modules/ops/services/ci/tools/metric.py`
- `apps/api/app/modules/ops/services/ci/tools/history.py`
- `apps/api/app/modules/ops/services/ci/tools/cep.py`

**작업 내용**:
1. 각 Tool을 BaseTool 상속으로 수정
2. execute() 메서드 시그니처 통일
3. ToolResult 반환 형식 통일
4. 오류 처리 메서드 구현

### 1-2. Tool Registry 구현

**파일 생성**:
- `apps/api/app/modules/ops/services/ci/tools/registry.py`
  - `ToolType` enum
  - `ToolRegistry` class

**기존 파일 수정**:
- `apps/api/app/modules/ops/services/ci/tools/__init__.py`

**작업 내용**:
1. ToolRegistry 싱글톤 구현
2. Tool 자동 등록
3. Tool 동적 로딩
4. Tool 리스트 조회 API

### 1-3. Orchestrator 일반화

**파일 수정**:
- `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**변경 사항**:
```python
# Before
def run():
    ci_result = ci_tool.execute()
    graph_result = graph_tool.execute()
    metric_result = metric_tool.execute()
    # ...

# After
def run():
    tools_to_execute = self._select_tools()  # Plan 기반
    for tool_type in tools_to_execute:
        tool = TOOL_REGISTRY.get_tool(tool_type)
        result = await tool.execute(context)
        # ...
```

### 1-4. 오류 처리 및 UX 개선

**파일 생성**:
- `apps/api/app/modules/ops/services/ci/error_handler.py`
- `apps/api/app/modules/ops/services/ci/context_manager.py`

**작업 내용**:
1. 사용자 친화적 오류 메시지 정의
2. 부분 실패 처리 로직
3. 대체 결과 제시 옵션
4. 피드백 블록 추가

### 1-5. 테스트 및 검증

**테스트 항목**:
- [ ] Tool Interface 호환성 테스트
- [ ] Registry 동작 테스트
- [ ] 부분 실패 시나리오 테스트
- [ ] 오류 메시지 가독성 테스트

---

## 📚 Phase 2: 문서 검색 통합 (3주)

### 2-1. 검색 백엔드 선택

**선택지**:
1. **Elasticsearch** (권장)
   - 장점: 풍부한 기능, 커뮤니티, 성능
   - 단점: 자체 인프라 필요

2. **PostgreSQL Full-Text Search**
   - 장점: 별도 인프라 불필요
   - 단점: 기능 제한, 성능 저하

3. **Milvus** (Vector DB)
   - 장점: 의미 검색, AI 통합
   - 단점: 추가 인프라, 복잡도

**권장**: Elasticsearch (기존 운영 지식 활용 가능)

### 2-2. DocumentTool 구현

**파일 생성**:
- `apps/api/app/modules/ops/services/ci/tools/document.py`
  - `DocumentTool` class
  - `_search_documents()` 메서드
  - `_resolve_document_to_ci()` 메서드

**구현 내용**:
```python
class DocumentTool(BaseTool):
    async def execute(self, context: ToolContext) -> ToolResult:
        # 1. 질문 파싱
        query = context.plan.document.query

        # 2. CI 필터링 (scope 기반)
        ci_filter = self._get_ci_filter(context)

        # 3. 검색 실행
        results = await self._search_documents(
            query=query,
            tenant_id=context.tenant_id,
            ci_filter=ci_filter,
            limit=context.plan.document.limit
        )

        # 4. 결과 정리
        return ToolResult(
            type="document",
            status="ok" if results else "empty",
            rows=[...],
            meta={...},
            trace={...}
        )
```

### 2-3. Planner 업데이트

**파일 수정**:
- `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`

**변경 사항**:
```python
def _determine_document_spec(question: str) -> Optional[DocumentSpec]:
    """문서 검색 필요 판단"""
    keywords = {"가이드", "설정", "문서", "설명서", "어떻게"}
    if any(kw in question for kw in keywords):
        return DocumentSpec(enabled=True, query=question)
    return None

# create_plan()에서 호출
if document_spec := _determine_document_spec(normalized):
    plan.document = document_spec
```

**파일 수정**:
- `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`

**변경 사항**:
- Plan에 `document: Optional[DocumentSpec]` 필드 추가

### 2-4. Frontend 블록 추가

**파일 수정**:
- `apps/web/src/components/answer/BlockRenderer.tsx`

**구현 내용**:
```typescript
case "document":
    return (
        <div className="border rounded-lg p-4">
            <h3 className="font-semibold mb-4">관련 문서</h3>
            <table className="w-full">
                <thead>
                    <tr>
                        <th>제목</th>
                        <th>미리보기</th>
                        <th>출처</th>
                        <th>관련도</th>
                    </tr>
                </thead>
                <tbody>
                    {block.rows?.map(row => (
                        <tr key={row.document_id}>
                            <td className="font-medium">{row.title}</td>
                            <td className="text-sm text-slate-500">{row.content_preview}</td>
                            <td className="text-sm">{row.source}</td>
                            <td className="text-sm">
                                <ProgressBar value={row.relevance * 100} />
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
```

### 2-5. 테스트 및 검증

**테스트 항목**:
- [ ] 검색 백엔드 연결 테스트
- [ ] 문서 인덱싱 테스트
- [ ] 질문 의도 감지 테스트
- [ ] CI 범위 필터링 테스트
- [ ] E2E 테스트 (질문 → 문서 조회)
- [ ] 의미 검색 테스트

---

## 🎨 Phase 3: UX 개선 (2주)

### 3-1. 자연스러운 의도 분류

**파일 생성**:
- `apps/api/app/modules/ops/services/ci/planner/intent_classifier.py`

**구현 내용**:
```python
class IntentClassifier:
    INTENT_KEYWORDS = {
        "INFO": {...},
        "STATUS": {...},
        "TREND": {...},
        "COMPARE": {...},
        "GUIDE": {...},
        "ANALYZE": {...},
    }

    @staticmethod
    def classify(question: str) -> str:
        # 의도 분류 로직
        pass

    @staticmethod
    def classify_intent_details(question: str) -> Dict:
        # 상세 의도 분석
        return {
            "intent": "...",
            "has_temporal": True/False,
            "has_comparison": True/False,
            "has_scope": True/False,
            "has_document": True/False,
        }
```

### 3-2. 점진적 공개 UI

**파일 수정**:
- `apps/api/app/modules/ops/services/ci/response_builder.py`
- `apps/web/src/components/answer/BlockRenderer.tsx`

**구현 내용**:
- 블록 우선순위 지정 (중요한 것부터)
- 요약 블록 먼저 표시
- 상세 정보는 펼칠 수 있도록

### 3-3. 컨텍스트 추적 시스템

**파일 생성**:
- `apps/api/app/modules/ops/services/ci/context_manager.py`

**구현 내용**:
```python
class ContextManager:
    def __init__(self, session_id: str):
        self.ci_history: List[str] = []
        self.queries: List[str] = []
        self.current_scope: Optional[List[str]] = None

    def suggest_next_questions(self) -> List[str]:
        # 다음 질문 제안
        pass

    def track_query(self, question: str, ci_ids: List[str]):
        # 질문 추적
        pass
```

### 3-4. 다음 질문 제안

**파일 수정**:
- `apps/api/app/modules/ops/services/ci/actions.py`

**구현 내용**:
- 컨텍스트 기반 제안
- 관계 탐색 제안
- 문서 검색 제안
- 성능 분석 제안

### 3-5. 테스트 및 검증

**테스트 항목**:
- [ ] 의도 분류 정확도 테스트
- [ ] UI 렌더링 테스트
- [ ] 다음 질문 제안 테스트
- [ ] 사용자 만족도 조사

---

## 📊 Phase 4: 모니터링 및 피드백 (1주)

### 4-1. 피드백 수집 시스템

**파일 생성**:
- `apps/api/app/modules/ops/services/feedback_service.py`

**구현 내용**:
```python
@dataclass
class UserFeedback:
    session_id: str
    question: str
    response_id: str
    rating: int  # 1-5
    comment: Optional[str]
    timestamp: datetime

async def save_feedback(feedback: UserFeedback):
    # DB에 저장
    pass
```

### 4-2. 성능 모니터링

**파일 생성**:
- `apps/api/app/modules/ops/services/metrics_service.py`

**수집 항목**:
- 응답 시간 (P50, P95, P99)
- 도구별 실행 시간
- 오류율
- 캐시 히트율
- 사용자 만족도

### 4-3. 분석 대시보드

**파일 생성**:
- `apps/web/src/app/admin/ops-analytics/page.tsx`

**표시 항목**:
- 일일/주간 사용량
- 자주 묻는 질문
- 오류 핫스팟
- 사용자 만족도 추이
- 도구별 성능 현황

---

## 🎯 체크리스트

### Phase 1 체크리스트
- [ ] Tool Interface 정의서 작성
- [ ] BaseTool 기본 클래스 구현
- [ ] ToolContext, ToolResult 데이터클래스 구현
- [ ] ToolRegistry 구현 및 테스트
- [ ] 기존 5개 Tool 마이그레이션
- [ ] Orchestrator 수정 및 테스트
- [ ] 오류 처리 로직 구현
- [ ] Unit test 작성 (80% 커버리지)
- [ ] Code review 완료
- [ ] 배포 및 smoke test

### Phase 2 체크리스트
- [ ] 검색 백엔드 선택 및 인프라 구성
- [ ] DocumentTool 구현
- [ ] DocumentTool 테스트
- [ ] Planner 수정 (문서 의도 감지)
- [ ] Plan 스키마 확장
- [ ] Frontend 블록 타입 추가
- [ ] 블록 렌더러 구현
- [ ] E2E 테스트
- [ ] 문서 인덱싱 자동화
- [ ] 배포 및 smoke test

### Phase 3 체크리스트
- [ ] 의도 분류기 구현
- [ ] 의도 분류 테스트 (90% 정확도)
- [ ] 점진적 공개 UI 설계
- [ ] 블록 우선순위 지정
- [ ] 컨텍스트 관리자 구현
- [ ] 다음 질문 제안 로직
- [ ] Frontend UI/UX 개선
- [ ] 사용자 테스트
- [ ] 피드백 기반 개선
- [ ] 배포

### Phase 4 체크리스트
- [ ] 피드백 수집 시스템 구현
- [ ] 성능 모니터링 구성
- [ ] 메트릭 대시보드 구현
- [ ] 분석 쿼리 작성
- [ ] 모니터링 alert 설정
- [ ] 운영 문서 작성
- [ ] 모니터링 자동화
- [ ] 주간 분석 리포트 자동화

---

## 🔧 기술 스택

### Backend
- **Framework**: FastAPI
- **ORM**: SQLModel
- **Cache**: Redis (향후)
- **Search**: Elasticsearch (문서 검색)
- **Async**: asyncio, aiohttp

### Frontend
- **Framework**: Next.js 14
- **UI**: Radix UI, Tailwind CSS
- **State**: React hooks, Context API
- **Async**: async/await, SWR

### Infrastructure
- **Database**: PostgreSQL, Neo4j
- **Search**: Elasticsearch (선택)
- **Monitoring**: Prometheus, Grafana (향후)

---

## 📈 성공 지표

### Phase 1
- [ ] Tool Interface 호환성 100%
- [ ] 기존 기능 회귀 없음
- [ ] 오류 처리 완성도 90%

### Phase 2
- [ ] 문서 검색 정확도 85%
- [ ] 문서 의도 감지 정확도 90%
- [ ] 검색 응답 시간 < 1초

### Phase 3
- [ ] 의도 분류 정확도 90%
- [ ] 사용자 만족도 85점/100
- [ ] 제안된 질문 사용률 40%

### Phase 4
- [ ] 사용자 피드백 회수율 30%
- [ ] 평균 응답 시간 < 2초
- [ ] 부분 실패 복구율 90%

---

## 💰 예상 비용 (인적자원)

| Phase | 담당 | 주당 시간 | 총 시간 | 비고 |
|-------|------|----------|--------|------|
| 1 | Backend 1, Frontend 1 | 40 | 80 | 2주 |
| 2 | Backend 1, Frontend 1 | 60 | 180 | 3주 |
| 3 | Backend 1, Frontend 1 | 40 | 80 | 2주 |
| 4 | Backend 1, DevOps 0.5 | 30 | 40 | 1주 |
| **합계** | | | **380시간** | 약 9.5명·주 |

---

## 🚨 리스크 및 대응

| 리스크 | 영향도 | 확률 | 대응 |
|--------|--------|------|------|
| Elasticsearch 성능 저하 | High | Medium | Redis 캐시 추가 |
| 문서 인덱싱 지연 | Medium | Low | 비동기 인덱싱 |
| 의도 분류 정확도 부족 | High | Medium | LLM 기반 분류로 개선 |
| 기존 기능 회귀 | High | Low | 포괄적 테스트 |

---

## 📝 문서화 계획

- [ ] Tool Interface 개발자 가이드
- [ ] DocumentTool 운영 가이드
- [ ] API 문서 업데이트
- [ ] 사용자 가이드 작성
- [ ] 모니터링 매뉴얼
- [ ] 트러블슈팅 가이드

---

이 로드맵은 현재 상황을 기반으로 하며, 실제 진행 과정에서 조정될 수 있습니다.
각 phase가 완료될 때마다 회고(retrospective)를 통해 다음 phase 계획을 조정합니다.
