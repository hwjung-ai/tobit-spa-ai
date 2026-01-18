# P0 항목 완료 계획안

## 현황 요약

**Tool Migration**: ✅ 95%+ 완료
**P0 항목 평균 완성도**: ⚠️ 45-50% (완료 필요)

---

## P0 항목 우선순위 및 작업 분해

### 🔴 Phase 5: 즉시 필수 보안 항목 (1-2주)

#### Task 5.1: API Key 관리 시스템 (NEW - 완전 미구현)
**우선도**: 🔴 CRITICAL
**예상 소요**: 3-4일

**구현 내용**:
```python
# apps/api/app/modules/api_keys/models.py (NEW)
class TbApiKey(SQLModel, table=True):
    key_id: UUID
    user_id: UUID (FK to TbUser)
    key_hash: str (bcrypt 해시)
    key_prefix: str (preview용, 첫 8자)
    name: str
    scope: list[str]  # ["api:read", "api:write", "ci:read", ...]
    last_used_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
    created_by_trace_id: str

# apps/api/app/modules/api_keys/crud.py (NEW)
def create_api_key(user_id, name, scope) -> str  # 생성 시만 전체 key 표시
def validate_api_key(key: str) -> tuple[UUID, list[str]]  # 검증
def revoke_api_key(key_id)
def list_user_api_keys(user_id)

# apps/api/app/modules/api_keys/router.py (NEW)
POST   /api-keys           - API Key 생성
GET    /api-keys          - 목록 조회
DELETE /api-keys/{key_id} - API Key 삭제

# apps/api/core/auth.py (MODIFY)
async def get_current_user_from_api_key(key: str) -> TbUser:
    # Authorization: Bearer <api-key>로 API Key 기반 인증
```

**작업 단계**:
1. TbApiKey 모델 정의 및 마이그레이션
2. CRUD 함수 구현
3. API Key 검증 미들웨어 추가
4. REST API 엔드포인트 구현
5. 테스트 작성

---

#### Task 5.2: 리소스 레벨 권한 정책 (PARTIAL - 50% 구현)
**우선도**: 🔴 CRITICAL
**예상 소요**: 4-5일

**구현 내용**:
```python
# apps/api/app/modules/permissions/models.py (NEW)
class ResourcePermission(str, Enum):
    # API 권한
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_DELETE = "api:delete"
    API_EXECUTE = "api:execute"

    # CI 권한
    CI_READ = "ci:read"
    CI_WRITE = "ci:write"
    CI_DELETE = "ci:delete"

    # UI 권한
    UI_READ = "ui:read"
    UI_WRITE = "ui:write"

    # 데이터 권한
    DATA_READ = "data:read"
    DATA_EXPORT = "data:export"

    # 설정 권한
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

class RolePermissionMapping(SQLModel, table=True):
    mapping_id: UUID
    role: UserRole (Admin, Manager, Developer, Viewer)
    permission: ResourcePermission
    resource_type: str | None  # API, CI, UI, DATA, SETTINGS
    resource_id: str | None    # 특정 리소스 (NULL = 모든 리소스)

# apps/api/core/auth.py (MODIFY - 권한 체크 함수)
def require_permission(permission: ResourcePermission, resource_id: str | None = None):
    # 데코레이터: 엔드포인트 레벨 권한 체크

def check_resource_permission(user: TbUser, permission: ResourcePermission, resource_id: str | None = None) -> bool:
    # 런타임 권한 체크 함수

# 사용 예시:
@router.get("/apis/{api_id}")
@require_permission(ResourcePermission.API_READ)
async def get_api(api_id: str, current_user: TbUser):
    # API 읽기 권한 필요
```

**역할별 기본 권한**:
```
Admin:
  - 모든 권한 (api:*, ci:*, ui:*, data:*, settings:*)

Manager:
  - api:read, api:write, ci:read, ci:write
  - settings:read (자신의 테넌트만)
  - data:read, data:export

Developer:
  - api:read, api:write, ci:read
  - ui:read, ui:write
  - data:read

Viewer:
  - api:read, ci:read, ui:read, data:read
```

**작업 단계**:
1. ResourcePermission enum 정의
2. RolePermissionMapping 모델 및 마이그레이션
3. 권한 체크 함수 구현
4. 모든 공개 엔드포인트에 권한 체크 추가 (50+ 엔드포인트)
5. 테스트 작성

---

#### Task 5.3: 민감 데이터 암호화 (COMPLETE NEW - 0% 구현)
**우선도**: 🔴 CRITICAL
**예상 소요**: 3-4일

**구현 내용**:
```python
# apps/api/core/encryption.py (NEW)
from cryptography.fernet import Fernet
import os

class EncryptionManager:
    def __init__(self):
        # 환경변수에서 암호화 키 읽기
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        """평문을 암호화된 토큰으로 변환"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        """암호화된 토큰을 평문으로 변환"""
        return self.cipher.decrypt(token.encode()).decode()

# 싱글톤 인스턴스
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager

# apps/api/app/modules/auth/models.py (MODIFY)
from sqlalchemy import String
from sqlalchemy.orm import mapped_column

class TbUser(SQLModel, table=True):
    # ... 기존 필드들 ...
    email: str  # 암호화 대상
    phone: str | None = None  # 암호화 대상 (PII)

    @property
    def decrypted_email(self) -> str:
        return get_encryption_manager().decrypt(self.email)

    @decrypted_email.setter
    def decrypted_email(self, value: str):
        self.email = get_encryption_manager().encrypt(value)

# 암호화 대상 필드 목록:
# - TbUser: email, phone, password_hash (이미 bcrypt)
# - TbApiKey: key_hash (추가: secret field)
# - TbAuditLog: 민감 변경사항 (sensitive_changes 필드 추가)
```

**암호화 전략**:
- **필드별 암호화**: Email, Phone, API Key secrets
- **선택적 암호화**: 감사 로그의 민감한 값들
- **키 관리**: 환경변수 + Docker Secrets

**작업 단계**:
1. EncryptionManager 구현
2. 민감 필드 식별 및 마이그레이션 스크립트
3. 저장/로드 시 자동 암호/복호화
4. 테스트 작성
5. 환경변수/키 관리 문서화

---

### 🟠 Phase 6: 보안 기초 완성 (1주)

#### Task 6.1: HTTPS & 보안 헤더
**우선도**: 🟠 HIGH
**예상 소요**: 2-3일

```python
# apps/api/core/middleware.py (ADD)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # 보안 헤더 추가
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response

# main.py (MODIFY)
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)  # HTTP → HTTPS 리다이렉트

# 설정 (MODIFY)
# apps/api/core/config.py
HTTPS_REQUIRED: bool = True
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOWED_ORIGINS: list[str] = [os.getenv("FRONTEND_URL", "http://localhost:3000")]
```

---

#### Task 6.2: CORS & CSRF 보안
**우선도**: 🟠 HIGH
**예상 소요**: 1-2일

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        os.getenv("BACKEND_HOST", "localhost"),
        os.getenv("FRONTEND_HOST", "localhost"),
    ]
)
```

---

### 🔵 Phase 7: OPS AI 오케스트레이터 개선 (2-3주)

#### Task 7.1: LangGraph StateGraph 구현
**우선도**: 🔵 HIGH
**예상 소요**: 1주

```python
# apps/api/app/modules/ops/services/langgraph_v2.py (NEW)
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated

class OrchestratorState(TypedDict):
    """오케스트레이터 상태"""
    question: str
    plan: Plan
    context: Dict[str, Any]
    tools_results: Dict[str, Any]
    current_step: int
    messages: List[Dict]
    metadata: Dict

# StateGraph 빌드
def build_orchestrator_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    # 노드들
    graph.add_node("plan", node_create_plan)
    graph.add_node("select_tools", node_select_tools)
    graph.add_node("execute_tools", node_execute_tools)
    graph.add_node("aggregate", node_aggregate_results)
    graph.add_node("format_response", node_format_response)

    # 엣지들
    graph.add_edge("plan", "select_tools")
    graph.add_conditional_edges(
        "select_tools",
        lambda state: "execute_tools" if state["plan"].steps else "format_response"
    )
    graph.add_edge("execute_tools", "aggregate")
    graph.add_edge("aggregate", "format_response")
    graph.set_entry_point("plan")

    return graph.compile()

# 사용:
async def run_with_langgraph(question: str) -> tuple[List[Block], List[str]]:
    orchestrator = build_orchestrator_graph()
    initial_state = OrchestratorState(
        question=question,
        plan=None,
        context={},
        tools_results={},
        current_step=0,
        messages=[],
        metadata={}
    )

    final_state = orchestrator.invoke(initial_state)
    return final_state["blocks"], final_state["raw_answers"]
```

---

#### Task 7.2: 재귀적 질의 해결
**우선도**: 🔵 MEDIUM
**예상 소요**: 3-4일

```python
# 오케스트레이터에서 구현
async def resolve_recursive_query(question: str, max_depth: int = 3, current_depth: int = 0):
    """
    복잡한 질의를 하위 질의로 분해하여 해결

    예: "DB 성능이 나빠진 이유와 해결방법은?"
    → 1. "DB 성능 메트릭 조회"
    → 2. "느린 쿼리 식별"
    → 3. "인덱스 분석"
    → 4. "리소스 병목 분석"
    → 통합 답변 생성
    """

    if current_depth >= max_depth:
        # 깊이 제한 도달
        return await simple_query_execute(question)

    # LLM이 하위 질의 생성
    sub_questions = await llm_decompose_query(question)

    sub_results = []
    for sub_q in sub_questions:
        result = await resolve_recursive_query(sub_q, max_depth, current_depth + 1)
        sub_results.append(result)

    # 결과 통합
    return await llm_aggregate_results(question, sub_results)
```

---

### 🟣 Phase 8: CI 관리 기능 (1-2주)

#### Task 8.1: CI 변경 추적
**우선도**: 🟣 MEDIUM
**예상 소요**: 3-5일

```python
# apps/api/app/modules/ci/models.py (ADD)
class TbCiChangeLog(SQLModel, table=True):
    change_id: UUID
    ci_id: UUID (FK to TbCi)
    trace_id: str
    action: str  # CREATE/UPDATE/DELETE/MERGE
    old_value: Dict[str, Any] | None
    new_value: Dict[str, Any] | None
    changed_by: UUID (FK to TbUser)
    changed_at: datetime
    reason: str | None  # 변경 사유

# CI 변경 감시 (미들웨어 또는 훅)
def track_ci_change(ci_id, old_value, new_value, user_id, action):
    change_log = TbCiChangeLog(
        ci_id=ci_id,
        trace_id=get_request_context()["trace_id"],
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=user_id,
        changed_at=datetime.now(),
    )
    db.add(change_log)
    db.commit()
```

---

#### Task 8.2: CI 데이터 정합성 검증
**우선도**: 🟣 MEDIUM
**예상 소요**: 2-3일

```python
# apps/api/app/services/ci_integrity.py (NEW)
async def check_ci_integrity():
    """정기적으로 CI 데이터 정합성 검증"""

    # 1. 중복 CI 감지
    duplicates = await detect_duplicate_cis()
    if duplicates:
        await create_integrity_alert("Duplicate CIs detected", duplicates)

    # 2. 고아 레코드 감지 (참조되지 않는 CI)
    orphans = await detect_orphan_cis()
    if orphans:
        await create_integrity_alert("Orphan CIs detected", orphans)

    # 3. 관계 일관성 검증
    invalid_relations = await validate_relationships()
    if invalid_relations:
        await create_integrity_alert("Invalid relationships", invalid_relations)

    # 정기 실행 (APScheduler 사용)
    # 매일 자정에 실행
    scheduler.add_job(check_ci_integrity, 'cron', hour=0, minute=0)
```

---

## 작업 우선순위 및 소요 시간

```
Phase 5: 즉시 필수 보안 (1-2주)
  ├─ Task 5.1: API Key 관리           3-4일   🔴 CRITICAL
  ├─ Task 5.2: 리소스 권한 정책       4-5일   🔴 CRITICAL
  └─ Task 5.3: 민감 데이터 암호화     3-4일   🔴 CRITICAL
              소계: 10-13일

Phase 6: 보안 기초 완성 (1주)
  ├─ Task 6.1: HTTPS & 헤더           2-3일   🟠 HIGH
  └─ Task 6.2: CORS & CSRF            1-2일   🟠 HIGH
              소계: 3-5일

Phase 7: OPS AI 개선 (2-3주)
  ├─ Task 7.1: LangGraph StateGraph    1주     🔵 HIGH
  └─ Task 7.2: 재귀적 질의            3-4일   🔵 MEDIUM
              소계: 10-11일

Phase 8: CI 관리 (1-2주)
  ├─ Task 8.1: CI 변경 추적           3-5일   🟣 MEDIUM
  └─ Task 8.2: 정합성 검증           2-3일   🟣 MEDIUM
              소계: 5-8일

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
총 소요 시간: 28-37일 (약 4-5주)
```

---

## 권장 구현 순서

```
1주차:
  Mon-Tue: Task 5.1 (API Key)          ~ 3-4일
  Wed-Thu: Task 5.2 (권한)              ~ 4-5일 (겹침)
  Fri:     Task 6.1 (HTTPS)             ~ 1-2일

2주차:
  Mon-Tue: Task 5.3 (암호화)            ~ 3-4일
  Wed:     Task 6.2 (CORS)              ~ 1-2일
  Thu-Fri: Phase 5-6 테스트 및 수정     ~ 2-3일

3주차:
  Mon-Wed: Task 7.1 (LangGraph)         ~ 1주
  Thu-Fri: Task 7.2 시작                ~ 2-3일

4주차:
  Mon-Tue: Task 7.2 (재귀 질의)         ~ 3-4일
  Wed-Fri: Task 8.1, 8.2 (CI 관리)      ~ 5-8일

5주차:
  Mon-Fri: 전체 테스트, 버그 수정, 최적화

6주차:
  프로덕션 준비 및 배포
```

---

## 예상 최종 상태

| 항목 | 현재 | 완료 후 |
|------|------|---------|
| **P0 완성도** | 45-50% | **95%+** ✅ |
| **보안** | 낮음 | 높음 ✅ |
| **테스트** | 부분 | 전체 ✅ |
| **배포 준비** | 미흡 | 완료 ✅ |

---

## 시작 준비

**즉시 시작 가능**: ✅ YES

**필요한 것**:
- 개발 환경: Python 3.10+, PostgreSQL, Redis
- 라이브러리: cryptography, langchain, langgraph
- 환경변수: ENCRYPTION_KEY 추가 필요

**첫 태스크**: Task 5.1 (API Key 관리)부터 시작

---

**권장 결정**: 지금 바로 Phase 5 Task 5.1부터 시작하시면 4-5주 내에 P0을 95%+ 완료할 수 있습니다! 🚀
