# 범용 오케스트레이션 시스템 - 실행 흐름

## 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────────┐
│                         사용자 질의                                   │
│  예: "공장의 장비 상태를 알려줘" / "maintenance 이력을 조회해"        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OPS (Orchestration) Router                         │
│  - 질의 분석 (질문 분류)                                             │
│  - 도메인 Planner 선택                                              │
└────────────────┬──────────────────────────┬──────────────────────────┘
                 │                          │
         ┌───────▼────────┐        ┌───────▼──────────┐
         │ CI Domain      │        │ Generic Domain   │
         │ (특화 플래너)   │        │ (범용 플래너)     │
         │ - CI 질의만    │        │ - 모든 질의      │
         │ - 하드코딩 로직 │        │ - LLM 기반       │
         └───────────────┘        └───────┬──────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────────┐
                        │  LLM Tool Selector                   │
                        │  (Generic Planner 내부)              │
                        ├─────────────────────────────────────┤
                        │ 1. Tool Registry에서 모든 Tool 목록  │
                        │    조회                              │
                        │                                      │
                        │ 2. 각 Tool의 description 추출:       │
                        │    - "장비 검색. 키워드: 장비, 설비"  │
                        │    - "유지보수 이력. 키워드: 정비"    │
                        │    - "생산 현황. 키워드: 생산"        │
                        │    - ... (6개 모두)                   │
                        │                                      │
                        │ 3. LLM에 다음 정보 제공:             │
                        │    - 사용자 질의: "장비 상태"         │
                        │    - Tool 목록 + descriptions        │
                        │    - Tool input schemas              │
                        │                                      │
                        │ 4. LLM이 적합한 Tool 선택:           │
                        │    - equipment_search (신뢰도 0.95)  │
                        │    - production_status (신뢰도 0.82) │
                        │                                      │
                        │ 5. 실행 순서 결정:                   │
                        │    - "parallel" (독립적)              │
                        └────────┬──────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │ GenericPlan 생성        │
                    │ {                       │
                    │  question: "...",       │
                    │  selected_tools: [      │
                    │    {                    │
                    │     tool_name:          │
                    │     "equipment_search", │
                    │     confidence: 0.95,   │
                    │     parameters: {...}   │
                    │    },                   │
                    │    {...}                │
                    │  ],                     │
                    │  execution_order:       │
                    │  "parallel"             │
                    │ }                       │
                    └────────┬────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │  Tool Chain Executor             │
              │  (Parallel 실행)                 │
              ├──────────────────────────────────┤
              │                                  │
              │  Tool 1: equipment_search        │
              │  ├─ Source: primary_postgres     │
              │  ├─ Query: SELECT * FROM eq...  │
              │  ├─ Input: {keyword: "장비"}     │
              │  └─ Result: [{id: 1, name:...}] │
              │                                  │
              │  Tool 2: production_status       │
              │  ├─ Source: primary_postgres     │
              │  ├─ Query: SELECT * FROM prod... │
              │  ├─ Input: {status: "running"}   │
              │  └─ Result: [{order_id: 123...}]│
              │                                  │
              │  ... (모든 선택된 Tool 병렬 실행) │
              │                                  │
              └────────┬─────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  결과 종합 & 응답 생성         │
        ├──────────────────────────────┤
        │ - 여러 Tool 결과 통합         │
        │ - LLM이 자연스러운 답변 생성   │
        │ - 사용자에게 반환             │
        └──────────────────────────────┘
```

---

## 단계별 상세 설명

### 1단계: 사용자 질의 수신
```
사용자: "장비 상태를 알려줘"
```

### 2단계: Domain Planner 선택
**OPS Router** → Domain Planners 중 가장 적합한 것 선택
- CI 도메인 플래너 (CI 질의만)
- **Generic Planner** ← 공장 질의는 여기서 처리

### 3단계: LLM이 적합한 Tool 찾기 (핵심!)

#### 3.1 Tool Registry에서 모든 Tool 조회
```python
# Tool Registry의 등록된 Tool 목록:
- equipment_search        (공장 장비 검색)
- maintenance_history     (유지보수 이력)
- bom_lookup             (BOM 조회)
- production_status      (생산 현황)
- worker_schedule        (근무자 일정)
- energy_consumption     (에너지 소비)
```

#### 3.2 LLM에게 제공되는 정보
```
프롬프트:
"다음 도구 중에서 사용자의 질문 '장비 상태를 알려줘'에
가장 적합한 도구를 선택하세요:

1. equipment_search
   설명: 공장 장비 검색. 키워드: 장비, 설비, equipment, machine
   입력스키마: {keyword: string, limit: integer}

2. maintenance_history
   설명: 장비 유지보수 이력 조회. 키워드: 유지보수, 점검, 정비
   입력스키마: {equipment_id: string, limit: integer}

3. production_status
   설명: 생산 현황 조회. 키워드: 생산, 제조, 현황, 상태
   입력스키마: {status: enum, limit: integer}

... (총 6개 Tool)
"
```

#### 3.3 LLM의 선택 결과
```json
{
  "tools": [
    {
      "tool_name": "equipment_search",
      "confidence": 0.95,
      "reasoning": "사용자가 '장비 상태'를 물었으므로 equipment_search가 가장 적합",
      "parameters": {
        "keyword": "상태"
      }
    },
    {
      "tool_name": "production_status",
      "confidence": 0.82,
      "reasoning": "생산 현황도 관련이 있을 수 있음",
      "parameters": {
        "status": "running"
      }
    }
  ],
  "execution_order": "parallel"
}
```

### 4단계: Tool Chain Executor - 병렬 실행

```python
# 동시에 두 Tool 실행
Task 1: equipment_search
  - Tool Name: equipment_search
  - Tool Type: database_query
  - Source: primary_postgres (DB 연결 정보)
  - Query Template: "SELECT * FROM equipment WHERE ..."
  - Input: {keyword: "상태"}
  - Execute: primary_postgres에 쿼리 실행
  - Result: [{id: 1, name: "장비-001", status: "정상"}, ...]

Task 2: production_status (동시 실행)
  - Tool Name: production_status
  - Tool Type: database_query
  - Source: primary_postgres
  - Query Template: "SELECT * FROM production_order WHERE ..."
  - Input: {status: "running"}
  - Execute: primary_postgres에 쿼리 실행
  - Result: [{order_id: "ORD-123", status: "진행중"}, ...]

# 두 결과 모두 대기 후 통합
```

### 5단계: 응답 생성 및 반환

LLM이 여러 Tool의 결과를 종합하여 자연스러운 답변 생성:
```
시스템: "현재 공장의 장비 상태는 다음과 같습니다:

▪ 활성 장비: 12개 (모두 정상 운영)
  - 장비-001: 정상
  - 장비-002: 정상
  - ...

▪ 진행 중인 생산:
  - ORD-123: 70% 진행 중
  - ORD-124: 준비 중
  - ...

특이사항 없음."
```

---

## 각 Asset의 역할

### ✅ Tool Asset (필수)
- **역할**: 실행 가능한 작업 정의
- **예시**: equipment_search, maintenance_history
- **정보 포함**:
  - 설명 (LLM이 선택할 때 사용)
  - 입력 스키마 (LLM이 파라미터 추출할 때 사용)
  - 실행 방식 (database_query, http_api 등)

### ✅ Source Asset (필수 - Tool 실행 시)
- **역할**: 데이터 소스 연결 정보
- **예시**: primary_postgres (DB 호스트, 포트, 인증 정보)
- **사용 시점**: Tool이 실제로 데이터를 가져올 때
- **관계**: Tool의 `tool_config.source_ref`로 참조

### ✅ Query Asset (선택 - 복잡한 쿼리 시)
- **역할**: 미리 작성한 쿼리 템플릿
- **예시**: CI 질의용 쿼리들
- **사용 시점**: 쿼리가 복잡할 때 (Tool이 query_ref로 참조)
- **현재 상황**: Tool이 inline query template 사용 중

### ✅ Mapping Asset (선택 - 키워드 기반 선택 시)
- **역할**: 키워드 ↔ Tool 매핑 (보조용)
- **예시**: "장비" 키워드 → equipment_search Tool
- **사용 시점**: LLM 선택 실패 시 Fallback 방식
- **현재 상황**: LLM 기반이므로 필요 없음

### ❌ Prompt Asset (미사용)
- **이유**: 각 플래너가 내장 프롬프트 사용 중

### ❌ Schema Asset (미사용)
- **이유**: Tool의 입력/출력 스키마로 충분

---

## 데이터 흐름 요약

```
Tool 설명 "장비 검색. 키워드: 장비, 설비"
          ↓
      LLM Tool Selector
      (적합성 판단: 0.95)
          ↓
Tool 실행 (Tool Chain Executor)
    ├─ Tool Config 로드 (source_ref, query_template)
    ├─ Source Asset 로드 (DB 연결 정보)
    ├─ 쿼리 실행 (Primary PostgreSQL)
    └─ 결과 반환
          ↓
      답변 생성 및 반환
```

---

## 예상 시나리오

### 시나리오 1: "공장에서 지금 생산 중인 제품은?"
```
1. LLM이 production_status, worker_schedule 선택
2. 두 Tool 병렬 실행
3. 결과: "현재 ORD-123, ORD-124, ORD-125 진행 중.
         근무자는 A조, B조 배치됨"
```

### 시나리오 2: "장비-001의 유지보수 이력은?"
```
1. LLM이 maintenance_history 선택 (신뢰도 1.0)
2. Tool 실행 (equipment_id="장비-001")
3. 결과: "지난 3개월간 5회 유지보수.
        마지막 정비: 2026-01-15"
```

### 시나리오 3: "에너지 사용이 많은 시간은?"
```
1. LLM이 energy_consumption, production_status 선택
2. 두 Tool 병렬 실행
3. 결과: "오전 9-11시 피크 시간.
        생산이 최고조일 때 전력 소비 급증"
```

---

## 정리: 다른 Asset이 필요한가?

### 현재 구조에서는:
- ✅ **Tool Asset만으로도 기본 작동 가능**
- ✅ **Source Asset**: Tool이 실제 데이터를 가져올 때 필요
- ✅ **Query Asset**: 복잡한 쿼리가 있을 때 선택적으로 사용
- ❌ **Mapping Asset**: LLM이 있으므로 필수 아님 (Fallback용)
- ❌ **Prompt Asset**: 각 플래너의 내장 프롬프트로 충분

### 따라서:
**Tool Asset + Source Asset이면 완전한 오케스트레이션 가능!** ✓

다른 Asset들은 **특정 도메인이나 고급 기능**에만 필요합니다.
