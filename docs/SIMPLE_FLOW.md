# 범용 오케스트레이션 - 핵심 흐름 (간단 버전)

## 한 문장으로 설명

**사용자 질의 → LLM이 적합한Tool들 선택 → 병렬/순차 실행 → 답변**

---

## 시각화

```
┌─────────────────────┐
│   사용자 질의        │
│ "장비 상태 알려줘"   │
└──────────┬──────────┘
           │
           ▼
    ┌─────────────────────────────┐
    │  LLM Tool Selector (핵심!)    │
    │                             │
    │ Tool 목록에서:              │
    │ ├─ equipment_search (0.95)  │ ← description으로
    │ ├─ production_status (0.82) │   판단
    │ ├─ maintenance_history (0.3)│
    │ ├─ bom_lookup (0.2)         │
    │ ├─ worker_schedule (0.4)    │
    │ └─ energy_consumption (0.1) │
    │                             │
    │ 선택: [0.95, 0.82]           │
    │ 순서: parallel               │
    └──────┬──────────────────────┘
           │
           ▼
    ┌─────────────────────────────┐
    │  Tool Chain Executor        │
    │                             │
    │  equipment_search           │
    │  ├─ Tool Config 로드        │
    │  ├─ Source Asset 로드       │
    │  │  (primary_postgres)      │
    │  ├─ 쿼리 실행              │
    │  └─ ① {id:1, name:...}     │
    │                             │
    │  production_status (동시)    │
    │  ├─ Tool Config 로드        │
    │  ├─ Source Asset 로드       │
    │  ├─ 쿼리 실행              │
    │  └─ ② {order_id:123...}    │
    │                             │
    │  결과 통합: [①, ②]          │
    └──────┬──────────────────────┘
           │
           ▼
    ┌─────────────────────┐
    │   답변 생성          │
    │ "장비 12개 정상,     │
    │  생산은 진행 중..."  │
    └─────────────────────┘
```

---

## Tool이 실행되는 과정

### Tool Config 구조 예시

```json
{
  "name": "equipment_search",
  "description": "공장 장비 검색. 키워드: 장비, 설비, equipment",
  "tool_type": "database_query",
  "tool_config": {
    "source_ref": "primary_postgres",      ← Source Asset 참조
    "query_template": "SELECT * FROM equipment WHERE ...",
    "timeout_ms": 30000
  },
  "tool_input_schema": {
    "properties": {
      "keyword": {"type": "string"}
    }
  }
}
```

### Tool 실행 단계

```
1️⃣  Tool Config 로드
    tool_config = equipment_search.tool_config

2️⃣  Source Asset 로드 (필요!)
    source = load_asset("primary_postgres")
    {
      "host": "115.21.12.151",
      "port": 5432,
      "database": "spadb",
      "user": "spa",
      "password": "***"
    }

3️⃣  DB 연결
    conn = connect_to(source)

4️⃣  쿼리 실행
    result = conn.execute(
      "SELECT * FROM equipment WHERE name ILIKE '%상태%' LIMIT 10"
    )

5️⃣  결과 반환
    [
      {id: 1, name: "장비-001", status: "정상"},
      {id: 2, name: "장비-002", status: "정상"},
      ...
    ]
```

---

## Asset 간 관계도

```
┌─────────────────────────────────────────────────────────┐
│                     Tool Asset                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ name: equipment_search                           │   │
│  │ description: "공장 장비 검색. 키: 장비, 설비"     │   │
│  │ tool_type: database_query                        │   │
│  │ tool_config: {                                   │   │
│  │   source_ref: "primary_postgres" ──┐            │   │
│  │   query_template: "SELECT ..."     │            │   │
│  │ }                                   │            │   │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                                          │
                                          │ 참조
                                          ▼
                    ┌──────────────────────────────────┐
                    │      Source Asset                │
                    │  ┌────────────────────────────┐  │
                    │  │ name: primary_postgres     │  │
                    │  │ host: 115.21.12.151        │  │
                    │  │ port: 5432                 │  │
                    │  │ database: spadb            │  │
                    │  │ user: spa                  │  │
                    │  │ password: ***              │  │
                    │  └────────────────────────────┘  │
                    └──────────────────────────────────┘
```

---

## 흐름에서 각 Asset의 역할

| Asset | 필수 여부 | 사용 시점 | 역할 |
|-------|---------|---------|------|
| **Tool** | ✅ 필수 | 항상 | LLM이 선택할 Tool 목록 제공 |
| **Source** | ✅ 필수 | Tool 실행 시 | 데이터베이스/API 연결 정보 |
| **Query** | ⭕ 선택 | 복잡한 쿼리 필요 시 | 미리 작성한 쿼리 저장 |
| **Mapping** | ⭕ 선택 | LLM 실패 시 | 키워드 ↔ Tool 직접 매핑 |
| **Prompt** | ❌ 불필요 | - | 각 플래너의 내장 프롬프트 사용 |
| **Schema** | ❌ 불필요 | - | Tool의 입출력 스키마로 충분 |

---

## 결론

### 질문: "다른 Asset은 필요 없는 것 아닌가?"

**답변:**
- ✅ **Tool Asset만으로도 기본 작동 가능** (현재 상태)
- ✅ **Source Asset은 데이터를 가져올 때 필수** (DB 연결 정보)
- ⭕ **Query Asset**: 복잡한 SQL이 있으면 유용하지만, inline template으로도 가능
- ⭕ **Mapping Asset**: LLM이 있으면 필수 아님 (Fallback용)
- ❌ **Prompt Asset**: 필요 없음 (이미 구현됨)

### 따라서:
**"Tool Asset + Source Asset"이면 완전한 오케스트레이션 시스템 구축 가능!**

다른 Asset들은 특정 도메인이나 고급 기능에만 도움이 되는 것입니다.

---

## 실제 데이터 흐름 예시

### 사용자: "공장 장비 상태 확인"

```
① Input
   Question: "공장 장비 상태 확인"

② LLM Tool 선택
   Tool Registry 조회 (6개 Tool)
   ├─ equipment_search: desc="장비 검색" → 신뢰도 0.95 ✅
   ├─ maintenance_history: desc="유지보수 이력" → 신뢰도 0.3
   ├─ production_status: desc="생산 현황" → 신뢰도 0.82 ✅
   ├─ bom_lookup: desc="BOM 조회" → 신뢰도 0.1
   ├─ worker_schedule: desc="근무 일정" → 신뢰도 0.2
   └─ energy_consumption: desc="에너지" → 신뢰도 0.1

   선택된 Tool: [equipment_search, production_status]
   실행 순서: parallel

③ Tool 실행 (병렬)

   Task 1: equipment_search
   - source_ref: "primary_postgres"
   - Source 로드 (DB 연결)
   - Query 실행
   - Result: 12개 장비, 모두 정상

   Task 2: production_status (동시)
   - source_ref: "primary_postgres"
   - Source 로드 (DB 연결)
   - Query 실행
   - Result: 3개 주문 진행 중

④ 결과 통합 및 응답
   "공장 장비는 12개 모두 정상입니다.
    현재 진행 중인 생산 주문은 3개입니다."

⑤ Output
   응답
```

---

## 앞으로의 확장 방향

### 현재 (완성 상태)
```
Tool Asset → LLM Tool Selector → Tool Chain Executor → 답변
                                        ↓
                                 Source Asset 로드
```

### 확장 가능성 1: Query Asset 활용
```
Tool Asset
├─ inline query (현재)
└─ query_ref: "query_asset_123" (향후)
    ↓
Query Asset 로드 (미리 작성한 복잡한 쿼리)
```

### 확장 가능성 2: Mapping Asset 활용
```
LLM Tool Selector 실패 시
↓
Mapping Asset 기반 Fallback
(키워드 매칭으로 Tool 직접 선택)
```

### 확장 가능성 3: Tool 체이닝
```
Tool 1 실행 → 결과
                ↓ (데이터 연결)
             Tool 2 실행 → 결과
                           ↓ (데이터 연결)
                        Tool 3 실행 → 최종 답변

예: "장비-001의 유지보수 이력과 다음 점검 일정은?"
    1. equipment_search(keyword="장비-001") → equipment_id
    2. maintenance_history(equipment_id="123") → 이력
    3. maintenance_schedule(equipment_id="123") → 일정
    4. 통합 답변
```
