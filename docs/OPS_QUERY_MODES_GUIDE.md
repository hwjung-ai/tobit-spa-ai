# OPS 질의 모드 상세 가이드

**작성일**: 2026-02-06
**목적**: OPS 메뉴의 5가지 질의 모드 API 및 기능 설명

---

## 1. 개요

OPS 메뉴의 왼쪽 패널에는 **5가지 질의 모드**가 있습니다:
- **구성** (Configuration)
- **수치** (Metrics)
- **이력** (History)
- **연결** (Relations/Graph)
- **전체** (All)

각 모드는 다른 API 엔드포인트를 사용하며, 사용자 질문에 따라 다른 응답 형식과 표시 방식을 제공합니다.

---

## 2. API 엔드포인트 매핑

| UI 모드 | 백엔드 모드 | API 엔드포인트 | HTTP 메서드 |
|---------|-----------|----------------|-----------|
| **구성** | config | `POST /ops/query` | POST |
| **수치** | metric | `POST /ops/query` | POST |
| **이력** | hist | `POST /ops/query` | POST |
| **연결** | graph | `POST /ops/query` | POST |
| **전체** | all | `POST /ops/ci/ask` | POST |

### 2.1 세부 API 정보

#### 그룹 A: 단순 모드 쿼리 (config, metric, hist, graph)

**엔드포인트**: `POST /ops/query`

**요청 스키마**:
```python
class OpsQueryRequest(BaseModel):
    question: str          # 사용자 질문
    mode: str             # "config" | "metric" | "hist" | "graph"
```

**요청 예시**:
```bash
POST /ops/query
Content-Type: application/json
X-Tenant-Id: tenant_123
X-User-Id: user_456

{
  "question": "서버 CPU 사용량은 얼마나?",
  "mode": "metric"
}
```

**응답 구조**:
```json
{
  "status": "success",
  "data": {
    "answer": "응답 텍스트",
    "summary": "간단 요약",
    "blocks": [/* 시각화 블록 */],
    "trace": {
      "trace_id": "uuid",
      "stages": [/* 실행 단계 */]
    }
  }
}
```

---

#### 그룹 B: 복합 모드 쿼리 (all/CI Ask)

**엔드포인트**: `POST /ops/ci/ask`

**요청 스키마**:
```python
class CiAskRequest(BaseModel):
    question: str           # 사용자 질문
    include_tools: bool = True
    include_references: bool = True
    replan_trigger: Optional[ReplanTrigger] = None
```

**요청 예시**:
```bash
POST /ops/ci/ask
Content-Type: application/json
X-Tenant-Id: tenant_123
X-User-Id: user_456

{
  "question": "최근 장애 원인을 분석해주고 관련 문서를 찾아줘",
  "include_tools": true,
  "include_references": true
}
```

**응답 구조**:
```json
{
  "status": "success",
  "data": {
    "answer_envelope": {
      "answer": "응답 텍스트",
      "meta": {
        "route": "ci",
        "route_reason": "복합 분석 필요",
        "timing_ms": 2500,
        "summary": "요약",
        "used_tools": ["database_lookup", "document_search"],
        "trace_id": "uuid"
      },
      "blocks": [/* 시각화 블록 */]
    },
    "stage_snapshots": [/* 각 단계 실행 결과 */],
    "inspector_traces": [/* 상세 실행 추적 */]
  }
}
```

---

## 3. 각 모드의 기능 및 특성

### 3.1 구성 (Configuration) - mode: "config"

#### API 호출
```
POST /ops/query?mode=config
```

#### 목적
- **Configuration Item (CI)** 정보 조회
- 서버, 애플리케이션, 데이터베이스 등의 **구성 정보** 검색

#### 질문 예시
- "서버 'sys-web01' 정보는?"
- "개발 환경의 데이터베이스 구성은?"
- "API 서버 목록을 보여줘"

#### 응답 특성
- **구조화된 데이터**: 테이블 형식
- **블록 타입**: `table`, `text`, `references`
- **포함 정보**: CI ID, 이름, 상태, 속성, 메타데이터

#### 응답 예시
```json
{
  "answer": "sys-web01 서버의 구성 정보입니다.",
  "blocks": [
    {
      "type": "table",
      "title": "서버 구성",
      "rows": [
        ["속성", "값"],
        ["CI ID", "sys-web01"],
        ["상태", "운영중"],
        ["OS", "Linux 5.15"],
        ["CPU", "8 cores"],
        ["Memory", "32 GB"]
      ]
    }
  ]
}
```

#### UI 표시 방식
- **테이블**: 구성 정보를 행/열로 표시
- **텍스트**: 추가 설명
- **참고**: 관련 문서/링크

---

### 3.2 수치 (Metrics) - mode: "metric"

#### API 호출
```
POST /ops/query?mode=metric
```

#### 목적
- **실시간 또는 과거 메트릭** 조회
- CPU, 메모리, 디스크, 네트워크 사용량 등 **성능 지표** 조회

#### 질문 예시
- "지난 1시간 CPU 사용률 추이는?"
- "현재 메모리 사용량은?"
- "디스크 용량 부족 상황은?"

#### 응답 특성
- **시계열 데이터**: 시간대별 변화
- **블록 타입**: `timeseries`, `number`, `chart`
- **포함 정보**: 시간, 값, 단위, 임계값

#### 응답 예시
```json
{
  "answer": "지난 1시간 CPU 사용률입니다.",
  "blocks": [
    {
      "type": "timeseries",
      "title": "CPU 사용률 추이",
      "series": [
        {
          "name": "sys-web01",
          "data": [
            {"time": "2026-02-06T10:00:00Z", "value": 45},
            {"time": "2026-02-06T10:05:00Z", "value": 52},
            {"time": "2026-02-06T10:10:00Z", "value": 48}
          ]
        }
      ]
    },
    {
      "type": "number",
      "label": "현재 CPU 사용률",
      "value": 48,
      "unit": "%"
    }
  ]
}
```

#### UI 표시 방식
- **차트**: 시계열 데이터를 그래프로 표시
- **숫자 카드**: 현재값 강조
- **범례**: 서버/메트릭 구분

---

### 3.3 이력 (History) - mode: "hist"

#### API 호출
```
POST /ops/query?mode=hist
```

#### 목적
- **이벤트, 장애, 변경 이력** 조회
- 특정 서버의 **과거 발생 사건** 검색

#### 질문 예시
- "sys-web01의 최근 장애 이력은?"
- "어제 발생한 에러는?"
- "지난주 시스템 변경 내역은?"

#### 응답 특성
- **타임라인 형식**: 시간순 정렬
- **블록 타입**: `timeline`, `table`, `markdown`
- **포함 정보**: 타임스탬프, 이벤트 타입, 상세 내용

#### 응답 예시
```json
{
  "answer": "sys-web01의 최근 장애 이력입니다.",
  "blocks": [
    {
      "type": "timeline",
      "title": "장애 타임라인",
      "events": [
        {
          "time": "2026-02-05T14:30:00Z",
          "type": "ERROR",
          "title": "CPU spike",
          "description": "CPU 사용률이 95%로 급증"
        },
        {
          "time": "2026-02-05T14:35:00Z",
          "type": "RESOLVED",
          "title": "복구됨",
          "description": "프로세스 재시작으로 정상화"
        }
      ]
    }
  ]
}
```

#### UI 표시 방식
- **타임라인**: 시간순으로 이벤트 표시
- **색상 구분**: 장애(빨강), 복구(초록) 등
- **상세 정보**: 클릭시 확장

---

### 3.4 연결 (Relations/Graph) - mode: "graph"

#### API 호출
```
POST /ops/query?mode=graph
```

#### 목적
- **의존성 관계** 분석
- 서비스 간 **네트워크 연결**, **데이터 흐름** 시각화

#### 질문 예시
- "웹서버와 데이터베이스의 연결 경로는?"
- "sys-web01이 의존하는 서비스는?"
- "외부 API와의 연동 현황은?"

#### 응답 특성
- **그래프 구조**: 노드(서버/서비스) + 엣지(연결)
- **블록 타입**: `graph`, `network`, `path`
- **포함 정보**: 노드 상태, 연결 상태, 레이턴시

#### 응답 예시
```json
{
  "answer": "sys-web01의 의존성 관계입니다.",
  "blocks": [
    {
      "type": "graph",
      "title": "서비스 의존성",
      "nodes": [
        {
          "id": "node1",
          "label": "sys-web01",
          "type": "server",
          "status": "healthy"
        },
        {
          "id": "node2",
          "label": "db-main-01",
          "type": "database",
          "status": "healthy"
        }
      ],
      "edges": [
        {
          "from": "node1",
          "to": "node2",
          "label": "SQL queries",
          "latency": "5ms"
        }
      ]
    }
  ]
}
```

#### UI 표시 방식
- **네트워크 다이어그램**: 노드 위치 자동 배치
- **상태 표시**: 색상으로 상태 표시 (초록=정상, 빨강=장애)
- **호버 정보**: 마우스 올리면 상세 정보

---

### 3.5 전체 (All/CI Ask) - mode: "all" → `/ops/ci/ask`

#### API 호출
```
POST /ops/ci/ask
```

#### 목적
- **종합 분석**: 위의 4가지 모드를 **모두 활용**
- LLM 기반 **정보 종합 및 해석**
- **외부 데이터 통합**: 문서, 정책, 외부 API 등

#### 질문 예시
- "최근 장애의 원인을 분석해줄 수 있나?"
- "성능 문제를 진단하고 해결책을 제시해줘"
- "문서를 참고해서 설정을 확인해줄 수 있나?"

#### 응답 특성
- **다단계 실행**: Route Planning → Validation → Execution → Composition
- **도구 활용**: Database, Metrics, Document Search, Graph 등 모두 사용 가능
- **문서 통합**: 📚 DOCS 모듈의 Document Search 자동 포함
- **블록 타입**: 모든 타입 (table, timeseries, graph, markdown 등)
- **포함 정보**: 종합 분석, 근본 원인, 권장사항

#### 응답 예시
```json
{
  "status": "success",
  "data": {
    "answer_envelope": {
      "answer": "문제 분석:\n1. CPU 과다 사용...\n2. 원본 원인...\n해결 방안:\n1. 프로세스 최적화\n2. 리소스 증설",
      "meta": {
        "route": "ci",
        "route_reason": "복합 분석 질문",
        "timing_ms": 3200,
        "summary": "CPU 과다 사용 원인 분석 및 해결책 제시",
        "used_tools": [
          "metric_lookup",      // 수치 조회
          "database_query",     // 구성 정보
          "trace_history",      // 이력 조회
          "graph_analysis",     // 연결 분석
          "document_search"     // 📚 문서 검색 (NEW!)
        ],
        "trace_id": "550e8400-e29b-41d4-a716-446655440000"
      },
      "blocks": [
        {
          "type": "markdown",
          "content": "# 장애 분석 보고서\n..."
        },
        {
          "type": "timeseries",
          "title": "CPU 사용률",
          "series": [...]
        },
        {
          "type": "graph",
          "title": "영향범위",
          "nodes": [...],
          "edges": [...]
        },
        {
          "type": "references",
          "title": "참고 문서",
          "items": [
            {
              "type": "document",
              "title": "성능 최적화 가이드",
              "url": "/docs/performance-guide",
              "relevance": 0.92
            }
          ]
        }
      ]
    },
    "stage_snapshots": [
      {
        "stage": "route_plan",
        "status": "ok",
        "duration_ms": 500,
        "decision": "ORCHESTRATION"
      },
      {
        "stage": "validate",
        "status": "ok",
        "duration_ms": 300
      },
      {
        "stage": "execute",
        "status": "ok",
        "duration_ms": 1800,
        "tool_calls": [
          "metric_lookup",
          "database_query",
          "document_search"
        ]
      },
      {
        "stage": "compose",
        "status": "ok",
        "duration_ms": 400
      },
      {
        "stage": "present",
        "status": "ok",
        "duration_ms": 200
      }
    ]
  }
}
```

#### UI 표시 방식
- **스테이지 파이프라인**: 각 단계별 실행 결과 표시
- **도구 호출 추적**: 어떤 도구를 사용했는지 표시
- **다양한 블록**: 텍스트, 차트, 그래프, 테이블 혼합
- **참고 문서**: 검색된 문서 링크 표시 (NEW!)
- **실행 시간**: 각 단계별 소요 시간 표시

---

## 4. 응답 블록 타입 (Answer Blocks)

| 블록 타입 | 용도 | 예시 |
|----------|------|------|
| **text** | 일반 텍스트 설명 | "서버 상태 양호합니다" |
| **markdown** | 서식이 있는 문서 | # 제목, **굵게** 등 |
| **number** | 단일 수치 강조 | CPU: 45% |
| **table** | 구조화된 데이터 | 서버 목록, 설정값 등 |
| **timeseries** | 시계열 차트 | 메트릭 추이 그래프 |
| **chart** | 일반 차트 | 막대그래프, 원그래프 |
| **graph** | 네트워크 다이어그램 | 서비스 의존성 |
| **network** | 복잡한 네트워크 | 대규모 인프라 관계 |
| **timeline** | 타임라인 | 장애 이력 |
| **path** | 경로 분석 | 홉 수, 레이턴시 |
| **references** | 참고 자료 링크 | 문서, 정책, 쿼리 |

---

## 5. 문서 (DOCS) 모드 추가 계획

### 5.1 새로운 모드: "문서" (Document) - 향후 추가

```typescript
// 현재 UI_MODES (5개)
{ id: "ci", label: "구성", backend: "config" },
{ id: "metric", label: "수치", backend: "metric" },
{ id: "history", label: "이력", backend: "hist" },
{ id: "relation", label: "연결", backend: "graph" },
{ id: "all", label: "전체", backend: "all" },

// 추가될 모드 (6개)
{ id: "document", label: "문서", backend: "document" },
```

### 5.2 문서 모드 API 디자인

**엔드포인트**: `POST /ops/query?mode=document` 또는 `POST /ops/documents/search`

**요청**:
```json
{
  "question": "성능 최적화 관련 문서를 찾아줘",
  "mode": "document",
  "search_type": "hybrid",  // text, vector, hybrid
  "top_k": 10,
  "filters": {
    "document_types": ["pdf", "md"],
    "date_from": "2025-01-01"
  }
}
```

**응답**:
```json
{
  "answer": "성능 최적화 관련 문서 검색 결과입니다.",
  "blocks": [
    {
      "type": "references",
      "title": "관련 문서",
      "items": [
        {
          "type": "document",
          "title": "성능 최적화 가이드",
          "url": "/docs/performance-guide",
          "relevance": 0.94,
          "excerpt": "CPU 과다 사용 시 확인할 사항...",
          "source": "md",
          "page": 5
        }
      ]
    }
  ]
}
```

### 5.3 구현 방식

#### 옵션 1: 독립 모드 추가 (권장)
```
UI_MODES에 추가: { id: "document", label: "문서", backend: "document" }
API 엔드포인트: POST /ops/query?mode=document
내부 라우팅: DocumentSearchService 호출
```

#### 옵션 2: 전체 모드에 통합 (현재)
```
전체 모드에서 document_search 도구 자동 호출
별도 모드 불필요
```

### 5.4 UI 배치

**현재 모드 선택 순서**:
```
┌─────────────────────┐
│ 구성 | 수치 | 이력  │ → 추가될 예정
│ 연결 | 전체 | 문서  │ (6번째 위치)
└─────────────────────┘
```

또는 **삽입 위치**:
```
┌─────────────────────┐
│ 구성 | 수치 | 이력  │
│ 연결 | 문서 | 전체  │ (연결과 전체 사이)
└─────────────────────┘
```

---

## 6. 모드별 응답 흐름도

```
┌─────────────────────────────────────────────────────┐
│           사용자 질문 입력                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐              │
│  │   구성       │  │   수치       │              │
│  │ (config)    │  │ (metric)    │              │
│  │ ↓           │  │ ↓           │              │
│  │ 테이블      │  │ 차트        │              │
│  └──────────────┘  └──────────────┘              │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐              │
│  │   이력       │  │   연결       │              │
│  │ (hist)      │  │ (graph)     │              │
│  │ ↓           │  │ ↓           │              │
│  │ 타임라인    │  │ 네트워크    │              │
│  └──────────────┘  └──────────────┘              │
│                                                     │
│  ┌──────────────────────────────────┐             │
│  │   전체 (all/ci/ask)              │             │
│  │   LLM 종합 분석                  │             │
│  │ ↓                                │             │
│  │ 모든 도구 활용:                 │             │
│  │ - 구성 정보                      │             │
│  │ - 성능 메트릭                    │             │
│  │ - 이벤트 이력                    │             │
│  │ - 의존성 분석                    │             │
│  │ - 📚 문서 검색 (NEW!)            │             │
│  └──────────────────────────────────┘             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 7. 차별점 요약

| 항목 | 구성 | 수치 | 이력 | 연결 | 전체 |
|------|------|------|------|------|------|
| **API** | /ops/query | /ops/query | /ops/query | /ops/query | /ops/ci/ask |
| **데이터** | 구성정보 | 메트릭 | 이벤트 | 관계도 | 모두 |
| **시각화** | 테이블 | 차트 | 타임라인 | 그래프 | 혼합 |
| **LLM** | 아니오 | 아니오 | 아니오 | 아니오 | 예 |
| **도구** | DB | Metrics | History | Graph | 모두 |
| **문서** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **속도** | ⚡ 빠움 | ⚡ 빠움 | ⚡ 빠움 | ⚡ 빠움 | 🐢 느림 |
| **정확도** | 높음 | 높음 | 높음 | 높음 | 최고 |

---

## 8. 코드 참고 위치

### 프론트엔드
- UI 모드 정의: `/apps/web/src/app/ops/page.tsx:30-39`
- 모드 선택 로직: `/apps/web/src/app/ops/page.tsx`
- OpsSummaryStrip 컴포넌트: `/apps/web/src/components/ops/OpsSummaryStrip.tsx`

### 백엔드
- /ops/query 엔드포인트: `/apps/api/app/modules/ops/routes/query.py`
- /ops/ci/ask 엔드포인트: `/apps/api/app/modules/ops/routes/ci_ask.py`
- 모드 처리: `/apps/api/app/modules/ops/services/`

### 문서 통합 (NEW)
- Document Search API: `/apps/api/app/modules/document_processor/router.py`
- Tool Asset: `/apps/api/tools/init_document_search_tool.py`

---

## 9. 다음 단계: 문서 모드 추가

### Phase 1: UI 추가 (1-2일)
```typescript
// OpsSummaryStrip.tsx에 문서 모드 추가
UI_MODES에 { id: "document", label: "문서", backend: "document" } 추가
```

### Phase 2: API 라우팅 추가 (1일)
```python
# query.py에 document 모드 처리 추가
if mode == "document":
    results = await DocumentSearchService.search(...)
```

### Phase 3: 통합 테스트 (1-2일)
```bash
# 문서 모드 테스트
POST /ops/query?mode=document
```

### Phase 4: 성능 최적화 및 배포 (2-3일)

---

## 10. 사용 시나리오

### 시나리오 1: 단순 구성 조회
```
사용자: "서버 sys-web01의 정보는?"
→ 모드: 구성 선택
→ API: POST /ops/query { mode: "config", question: "..." }
→ 응답: 테이블 형식의 구성 정보
```

### 시나리오 2: 성능 추이 확인
```
사용자: "지난 1시간 CPU 사용률은?"
→ 모드: 수치 선택
→ API: POST /ops/query { mode: "metric", question: "..." }
→ 응답: 시계열 차트
```

### 시나리오 3: 장애 원인 종합 분석 (문서 포함)
```
사용자: "어제 발생한 장애의 원인을 분석해주고 관련 문서도 찾아줄 수 있니?"
→ 모드: 전체 선택
→ API: POST /ops/ci/ask { question: "..." }
→ 실행 단계:
   1. Route Planning: ORCHESTRATION 결정
   2. Validation: 필요 도구 확인
   3. Execution:
      - 메트릭 조회 (CPU, 메모리 그래프)
      - 구성 정보 조회 (서버 상태)
      - 이력 조회 (장애 이벤트)
      - 의존성 분석 (영향범위)
      - 📚 문서 검색 (성능 최적화 가이드)
   4. Composition: 정보 종합
   5. Presentation: 마크다운 + 차트 + 그래프 + 문서 링크
→ 응답: 종합 분석 보고서 (문서 참고 포함)
```

---

**문서 작성**: Claude AI
**버전**: 1.0
**날짜**: 2026-02-06
