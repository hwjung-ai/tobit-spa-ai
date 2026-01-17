# Operations Playbook - 운영 대응 가이드

**작성 일시**: 2026-01-18
**상태**: 최신 (통합 문서)
**대상**: 운영팀, 지원팀

이 문서는 Inspector 기반 문제 진단과 대응 방법을 단계별로 설명합니다.

---

## 📋 개요

### 8가지 핵심 시나리오
1. 답이 이상함 (응답 내용 오류)
2. 데이터 없음 (정상/비정상 구분)
3. Tool timeout (도구 실행 지연)
4. 외부 API 5xx (외부 의존성 오류)
5. 권한 오류 (401/403)
6. 데이터베이스 연결 오류
7. 성능 저하 (응답 시간 증가)
8. 메모리 부족 / 리소스 부족

### 대응 흐름
```
증상 인지
  ↓
Inspector 진단 (Trace 분석)
  ↓
Diff / Regression / RCA 분석
  ↓
원인 파악
  ↓
대응 (설정 변경, 롤백, API 호출, 등)
  ↓
재실행 & 검증
```

---

## 1️⃣ 답이 이상함

### 증상
응답 내 주요 항목(값, 개수, 설명)이 문맥과 맞지 않음.
예:
- "총 비용: 1000원" (실제 집계 결과: 100,000원)
- "서비스 개수: 5개" (실제: 50개)
- "의존성 없음" (실제: 10개 의존성 있음)

### 진단 절차

#### Step 1: Inspector 열기
```
Trace → answer.blocks → 해당 block (table/graph/text) → tool_calls
```

#### Step 2: Diff 분석
```
1. Diff 모듈에서 이 trace와 Baseline (동일 Golden Query) 비교
2. Regression 결과에서 PASS/WARN/FAIL 판정 확인
3. verdict_reason 검토
```

#### Step 3: RCA 규칙 검토
```
- "Plan Intent Shift" 규칙 (계획 의도 변경)
- "Tool Path Changes" 규칙 (도구 경로 변경)
```

### 대응 방법

#### 원인 1: Plan Intent Mismatch
**증상**: Planner가 잘못된 쿼리 계획 생성

**대응 단계**:
1. `apps/api/app/modules/ops/services/ci/planner/planner_llm.py` 검토
2. Planner prompt 수정 또는 새로운 Query Asset 생성
3. 테스트 케이스 추가: `apps/api/tests/test_planner.py`
4. 재실행 후 diff를 통해 block 변화 검증

#### 원인 2: Tool Path 오류
**증상**: Executor가 잘못된 도구 선택 또는 순서 오류

**대응 단계**:
1. Inspector → tool_calls 섹션에서 도구 순서 확인
2. `apps/api/app/modules/ops/services/executors/` config 검토
3. 불필요한 도구 제거 또는 config rollback
4. 재실행 후 PASS 상태 유지 확인

#### 원인 3: Query Asset 버그
**증상**: SQL/Cypher 쿼리 로직 오류

**대응 단계**:
1. Assets Admin → Query Asset 상세 페이지
2. [Rollback] 또는 [Edit] → 수정
3. 테스트 데이터로 결과 검증
4. [Publish] 클릭

### 검증
```
재실행 → Regression PASS 확인 → 운영 적용
```

---

## 2️⃣ 데이터 없음

### 증상
- `No data` 메시지 표시
- 로우 개수: 0건
- 반복적으로 row_count 감소

### 진단 절차

#### Step 1: Inspector 분석
```
Trace → references (SQL/Cypher/metric) → row_count → trace.meta.filters
```

#### Step 2: RCA 검토
```
- "No Data Ambiguity" 규칙으로 정상 무 결과인지 확인
- confidence=low 로 표기되는 경우 false positive 가능성
```

#### Step 3: Regression 비교
```
Baseline 대비 reference row_count 80% 이하 감소: WARN/FAIL 판정
```

### 대응 방법

#### 원인 1: 필터 범위 변경
**증상**: 조회 기간, 상태 필터 등이 변경됨

**대응 단계**:
1. Inspector → trace.meta.filters 확인
2. 의도한 범위와 비교
3. Query Asset 수정 필요 시 Edit → 필터 조정 → Publish
4. 재실행 후 데이터 수량 확인

#### 원인 2: 실제 데이터 부족
**증상**: 조회 대상 기간/범위에 실제 데이터 없음

**대응 단계**:
1. 데이터 수집 확인 (데이터소스가 정상인지 확인)
2. Ops checklist에 "데이터 수집 확인" 추가
3. 필요시 테스트 데이터 추가

#### 원인 3: 데이터베이스 연결 오류
**증상**: row_count = 0 + error in trace.meta.error

**대응 단계**:
1. Database health check (CONNECTION OK?)
2. 쿼리 실행 권한 확인
3. 타임아웃 설정 검토 (설정에서 db_query_timeout_seconds 확인)
4. 문제 지속 시 DBA 연락

### 검증
```
Baseline trace 재 capture → PASS 여부 확인 → 운영 적용
```

---

## 3️⃣ Tool Timeout

### 증상
- 도구 실행 시간 기준 초과
- `tool_call.error`에 `timeout` 문구

### 진단 절차

#### Step 1: Inspector 분석
```
Trace → execution_steps → duration_ms → error
```

#### Step 2: RCA 검토
```
"Tool Duration Spike" rule → evidence path jump
```

#### Step 3: Regression 검증
```
Timed out tool이 baseline에서 absent 또는 success인지 확인
```

### 대응 방법

#### 대응 1: Timeout 설정 조정
```python
# apps/api/app/modules/ops/services/tool_config.py

# 기존
TOOL_TIMEOUT = 30  # 초

# 수정
TOOL_TIMEOUT = 60  # 초 (느린 도구에 대해)
```

**선택 기준**:
- 외부 API 호출: 30-60초
- DB 복잡 쿼리: 60-120초
- 내부 도구: 10-30초

#### 대응 2: 재시도 정책
```python
TOOL_RETRY_ATTEMPTS = 3
TOOL_RETRY_BACKOFF = 2  # exponential backoff
```

#### 대응 3: 외부 API 확인
```
Timeout 도구가 외부 호출이면:
1. 외부 API 상태 확인 (API health page)
2. 네트워크 연결 상태 확인
3. API rate limit 확인
4. Fallback asset으로 전환 (선택사항)
```

### 검증
```
설정 변경 → GQ 재실행 → duration 감소 확인 → PASS 상태 유지
```

---

## 4️⃣ 외부 API 5xx

### 증상
- `tool_call.error.status` = 5xx
- External HTTP 도구
- `trace.references.kind` = "http"

### 진단 절차

#### Step 1: Inspector 분석
```
Trace → tool_calls → step_id → error.request
```

#### Step 2: RCA 검토
```
"HTTP 5xx" rule → evidence path jump → requests 확인
```

#### Step 3: Diff 분석
```
Baseline vs candidate response payload + references row count 비교
```

### 대응 방법

#### 대응 1: API 인증 확인
```
1. API Key / Token 유효성 점검
2. 권한 범위 확인
3. Rate limit 확인
4. 필요시 새 토큰 재발급
```

#### 대응 2: API 상태 확인
```
1. 외부 API health page 확인
2. 상태 페이지 (status.example.com) 확인
3. 관련팀에 연락 (API owner)
```

#### 대응 3: 재시도 정책
```
HTTP 5xx 지속 시:
- "retry after 5m" 또는
- "switch fallback asset" (대체 Query Asset 사용)
```

#### 대응 4: Fallback 전환
```
Settings Admin → ops_fallback_assets 설정
{
  "api_transactions": "api_transactions_fallback",
  "api_users": "api_users_cached"
}
```

### 검증
```
Regression 재실행 → FAIL 여부 확인 → Asset rollback 필요시 실행
```

---

## 5️⃣ 권한 오류 (401/403)

### 증상
- `HTTP 401` (Unauthorized)
- `HTTP 403` (Forbidden)
- `error: "Permission denied"`

### 진단 절차

#### Step 1: Inspector 분석
```
Trace → tool_calls → error.status → error.message
```

#### Step 2: 권한 정보 확인
```
Trace → context → current_user → roles / permissions
```

### 대응 방법

#### 원인 1: 만료된 토큰
**대응**:
1. 토큰 갱신 (POST /auth/refresh)
2. Settings Admin → JWT token rotation
3. 재실행

#### 원인 2: 사용자 권한 부족
**대응**:
1. 사용자 역할 확인 (Admin → Users)
2. 필요한 권한 부여 (역할 추가)
3. 재실행

#### 원인 3: API 리소스 접근 권한
**대응**:
1. Query Asset 권한 확인 (draft/published)
2. 필요시 권한 범위 확대
3. Rollback 검토

### 검증
```
권한 설정 변경 → 재실행 → 200 OK 확인
```

---

## 6️⃣ 데이터베이스 연결 오류

### 증상
- `database connection timeout`
- `connection pool exhausted`
- `connection refused`

### 진단 절차

#### Step 1: DB Health Check
```bash
$ curl http://localhost:8000/health
{
  "database": {
    "status": "⚠️ degraded",
    "active_connections": 25,
    "pool_size": 20
  }
}
```

#### Step 2: 연결 풀 상태
```
Settings Admin → db_connection_pool_size 확인
현재: 20, 사용 중: 25 (오버플로우)
```

### 대응 방법

#### 대응 1: 연결 풀 크기 증가
```
Settings Admin → db_connection_pool_size
20 → 30 으로 변경
재시작 필요 ⚠️
```

#### 대응 2: 느린 쿼리 확인
```
Observability Dashboard → Top Slow Queries
오래 실행되는 쿼리 찾기 → Query Asset 최적화
```

#### 대응 3: 데이터베이스 재시작
```
운영팀 또는 DBA:
1. 모든 연결 닫기
2. PostgreSQL 재시작
3. 헬스 체크 확인
```

### 검증
```
Health Check → 모든 상태 OK 확인
```

---

## 7️⃣ 성능 저하

### 증상
- API 응답 시간: 기준 대비 2배 이상
- Observability Dashboard: 응답 시간 스파이크

### 진단 절차

#### Step 1: 메트릭 확인
```
Observability Dashboard → Response Time Trend
- 24시간 그래프에서 스파이크 시점 확인
```

#### Step 2: Top Slow Queries 분석
```
- 어떤 Query가 느린가?
- 실행 시간 추이
```

#### Step 3: 시스템 리소스 확인
```
- CPU 사용률
- 메모리 사용률
- 디스크 I/O
```

### 대응 방법

#### 대응 1: Query 최적화
```
느린 Query Asset:
1. EXPLAIN 분석 (쿼리 실행 계획)
2. 인덱스 추가 또는 쿼리 수정
3. 테스트 후 Publish
```

#### 대응 2: 캐시 활성화
```
Settings Admin → ops_cache_ttl_seconds
0 (비활성) → 300 (5분) 으로 변경

캐시 적중률 모니터링 (목표: >80%)
```

#### 대응 3: 시스템 스케일링
```
- API 서버 인스턴스 증가 (Docker replicas)
- 데이터베이스 메모리 증가
- Redis 캐시 크기 증가
```

### 검증
```
변경 후 30분 모니터링 → 응답 시간 정상화 확인
```

---

## 8️⃣ 메모리 부족 / 리소스 부족

### 증상
- API 서버: OOMKilled (Out of Memory)
- 응답: `500 Internal Server Error`
- 로그: `MemoryError` 또는 `ResourceLimitExceeded`

### 진단 절차

#### Step 1: 리소스 모니터링
```bash
$ docker stats
CONTAINER    MEM USAGE
api          950MiB (limit: 1024MiB) ← 거의 가득 참
```

#### Step 2: 메모리 누수 확인
```
Observability Dashboard → Memory Trend
- 꾸준히 증가하는가? (누수 가능성)
- 주기적으로 증가/감소하는가? (정상 GC)
```

### 대응 방법

#### 대응 1: 메모리 할당 증가
```yaml
# docker-compose.yml
services:
  api:
    mem_limit: 2g  # 1g → 2g로 증가
```

#### 대응 2: 메모리 누수 찾기
```
1. 힙 덤프 분석 (Python profiler 사용)
2. 순환 참조 확인
3. 캐시 크기 제한 설정
```

#### 대응 3: 대용량 데이터 처리 최적화
```
- 페이지네이션 적용
- 스트리밍 결과 (대신 배치 로딩)
- 불필요한 데이터 필터링
```

### 검증
```
재시작 후 메모리 사용 추이 모니터링 (24시간)
```

---

## 🎯 실시간 대응 시나리오

### 시나리오 A: "갑자기 모든 질의가 실패"

**대응 순서**:
1. Health Check 확인 (모든 컴포넌트)
2. 최근 배포/설정 변경 확인 (git log, Settings admin)
3. 가장 최근 변경 Rollback
4. 시스템 재시작
5. 모니터링으로 복구 확인

**예상 시간**: 5-10분

### 시나리오 B: "특정 조회만 느려짐"

**대응 순서**:
1. Inspector에서 해당 trace 분석
2. Slow Query Log 확인
3. Query Asset 최적화 또는 Rollback
4. 캐시 설정 검토
5. 재실행

**예상 시간**: 10-20분

### 시나리오 C: "메모리 누수 의심"

**대응 순서**:
1. 메모리 사용 추이 확인 (24시간)
2. 메인 프로세스 재시작 (무중단)
3. 힙 덤프 분석 예약
4. 개발팀에 보고

**예상 시간**: 즉시 (재시작), 분석은 별도 진행

---

## 📊 모니터링 체크리스트

### 매시간
- [ ] Error Rate < 1% 확인
- [ ] Response Time p95 < 500ms
- [ ] Database 연결 정상

### 매일
- [ ] Observability Dashboard 전체 검토
- [ ] Top Slow Queries 분석
- [ ] 비정상 알림 로그 검토

### 주간
- [ ] 성능 트렌드 분석 (개선/악화)
- [ ] 용량 계획 (CPU, 메모리, 스토리지)
- [ ] 자산 변경 이력 검토 (최근 발행된 자산)

---

## 📞 에스컬레이션

### Level 1: 운영팀 (자체 해결 시간: 30분)
- 설정 변경
- 캐시 초기화
- 간단한 Rollback

### Level 2: DevOps 팀 (대응 시간: 1시간)
- Docker 재시작
- 데이터베이스 최적화
- 인프라 스케일링

### Level 3: 개발팀 (대응 시간: 수시)
- Query Asset 버그 수정
- Planner 로직 개선
- 메모리 누수 분석

---

**최종 업데이트**: 2026-01-18
**작성자**: Operations Team
**검수**: DevOps, Support

---

## 🔗 관련 링크

- **Observability Dashboard**: `/admin/observability`
- **Inspector**: `/ops` → 이력 탭 → 해당 trace 선택
- **Settings Admin**: `/admin/settings`
- **Health Check API**: `GET /health`
