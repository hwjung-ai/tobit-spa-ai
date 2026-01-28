# 범용 오케스트레이션 시스템 - 핵심 요약

## 📌 한 문장 설명

**"사용자가 물으면 → LLM이 가장 적합한 Tool들을 찾아 → 병렬로 실행하고 → 결과를 종합한 답변을 제공"**

---

## 🔄 실행 흐름 (5단계)

### 1️⃣ 사용자 질의 수신
```
사용자: "공장 장비 상태를 알려줘"
```

### 2️⃣ LLM이 적합한 Tool 찾기 (핵심!)
```
Tool Registry에서:
- equipment_search (신뢰도: 0.95) ✅ 선택
- production_status (신뢰도: 0.82) ✅ 선택
- maintenance_history (신뢰도: 0.3) ❌
- bom_lookup (신뢰도: 0.1) ❌
- worker_schedule (신뢰도: 0.2) ❌
- energy_consumption (신뢰도: 0.1) ❌

선택된 Tool: equipment_search, production_status
실행 방식: parallel (독립적이므로)
```

**LLM이 판단 근거:**
- Tool의 `description` 필드 읽음
  - "공장 장비 검색. 키워드: 장비, 설비, equipment"
  - "생산 현황 조회. 키워드: 생산, 제조, 현황"
- 사용자 질의와 매칭
- 신뢰도 계산

### 3️⃣ Tool Chain Executor - 병렬 실행

```
동시 실행:

Task 1: equipment_search
├─ Tool Config 로드 (query_template, source_ref)
├─ Source Asset 로드 (primary_postgres)
│  └─ DB 연결 정보: host, port, user, password
├─ SQL 쿼리 실행
│  └─ "SELECT * FROM equipment WHERE name ILIKE '%상태%'"
└─ 결과: [{id: 1, name: "장비-001", status: "정상"}, ...]

Task 2: production_status (동시 진행)
├─ Tool Config 로드
├─ Source Asset 로드 (primary_postgres)
├─ SQL 쿼리 실행
│  └─ "SELECT * FROM production_order WHERE status='running'"
└─ 결과: [{order_id: "ORD-123", status: "진행중"}, ...]

⏳ 모든 Task 완료 대기
```

### 4️⃣ 결과 통합
```
[
  {equipment_count: 12, status: "정상"},
  {orders: 3, status: "진행중"}
]
```

### 5️⃣ 답변 생성
```
LLM이 종합하여:
"공장의 장비는 현재 12개 모두 정상적으로 운영 중입니다.
 생산 중인 주문은 3개이며, 모두 일정대로 진행 중입니다."
```

---

## 🧩 Asset 간 연계

### 필수 Asset

#### Tool Asset (필수)
```json
{
  "name": "equipment_search",
  "description": "공장 장비 검색. 키워드: 장비, 설비",
  "tool_type": "database_query",
  "tool_config": {
    "source_ref": "primary_postgres",
    "query_template": "SELECT * FROM equipment WHERE ..."
  },
  "tool_input_schema": {
    "type": "object",
    "properties": {
      "keyword": {"type": "string"}
    }
  }
}
```

#### Source Asset (필수 - Tool 실행 시)
```json
{
  "name": "primary_postgres",
  "source_type": "postgresql",
  "connection": {
    "host": "115.21.12.151",
    "port": 5432,
    "database": "spadb",
    "user": "spa",
    "password": "***"
  }
}
```

**Tool이 실행될 때 Source Asset이 필요한 이유:**
- Tool의 `tool_config.source_ref`가 "primary_postgres"를 지정
- Tool이 실행되려면 DB 연결 정보 필요
- Source Asset에서 그 정보를 가져옴

### 선택적 Asset

| Asset | 필요 여부 | 언제 쓰는가 |
|-------|---------|-----------|
| **Query** | 선택 | 복잡한 SQL이 있을 때, Tool이 `query_ref`로 참조 |
| **Mapping** | 선택 | LLM 실패 시, 키워드 직접 매핑으로 Tool 선택 |
| **Prompt** | 불필요 | 각 플래너가 내장 프롬프트 사용 |
| **Schema** | 불필요 | Tool의 입출력 스키마로 충분 |

---

## ❓ FAQ: "다른 Asset이 필요 없나?"

### Q: Source Asset이 없으면?
**A:** Tool이 실행되지 않음. DB/API 연결 정보가 필수.

### Q: Query Asset이 없으면?
**A:** inline query template으로 충분. 선택사항.

### Q: Mapping Asset이 없으면?
**A:** LLM이 있으므로 자동으로 Tool 선택. Fallback 용도.

### Q: 현재 구조에서 필수 Asset?
**A:** Tool Asset + Source Asset만 있으면 완전히 작동함.

---

## 📊 데이터 흐름도

```
사용자 질의 (자연어)
    ↓
LLM Tool Selector
    ├─ Tool Registry 조회 (6개 Tool 목록)
    ├─ Tool descriptions 분석
    ├─ 신뢰도 계산
    └─ 선택된 Tool 목록 + 파라미터
    ↓
Tool Chain Executor (병렬/순차/DAG 실행)
    ├─ Tool 1 실행
    │  ├─ Config 로드
    │  ├─ Source Asset 로드 ← ⭐ 여기서 필요!
    │  ├─ DB/API 호출
    │  └─ 결과 1
    ├─ Tool 2 실행 (동시)
    │  ├─ Config 로드
    │  ├─ Source Asset 로드
    │  ├─ DB/API 호출
    │  └─ 결과 2
    └─ 결과 통합
    ↓
답변 생성 (LLM이 종합)
    ↓
사용자에게 반환
```

---

## 🎯 현재 상태 체크리스트

- ✅ Tool Asset 생성 (6개 데모 Tool)
- ✅ Tool Registry 구현
- ✅ LLM Tool Selector 구현
- ✅ GenericPlanner 구현
- ✅ Tool Chain Executor 구현
- ✅ Tool API 엔드포인트
- ✅ Admin UI (Tool 관리)
- ✅ Source Asset 존재 (primary_postgres)
- ✅ DB 마이그레이션 (Tool 칼럼 추가)

**결론: 완전히 작동 가능한 상태! ✓**

---

## 🚀 실행 예시

### 예시 1: "장비-001의 정보는?"

```
1. 사용자: "장비-001의 정보는?"

2. LLM 분석:
   equipment_search (0.98) ✅
   maintenance_history (0.4)
   → equipment_search 선택

3. Tool 실행:
   equipment_search({keyword: "장비-001"})
   ├─ Source: primary_postgres
   ├─ Query: SELECT * FROM equipment WHERE name='장비-001'
   └─ Result: {id: 1, name: "장비-001", status: "정상", location: "생산 라인 A"}

4. 답변:
   "장비-001은 생산 라인 A에 위치하며, 현재 정상적으로 운영 중입니다."
```

### 예시 2: "지금 생산 상황과 에너지 사용량은?"

```
1. 사용자: "지금 생산 상황과 에너지 사용량은?"

2. LLM 분석:
   production_status (0.95) ✅
   energy_consumption (0.92) ✅
   worker_schedule (0.3)
   → [production_status, energy_consumption] 선택
   → execution_order: parallel

3. Tool 실행 (병렬):
   Task 1: production_status()
   └─ 3개 주문 진행 중

   Task 2: energy_consumption({start: now-1h, end: now})
   └─ 현재 전력 소비 500kW

4. 답변:
   "현재 3개의 생산 주문이 진행 중이며,
    에너지 사용량은 500kW로 정상 범위입니다."
```

### 예시 3: "장비-001의 이력과 다음 점검은?"

```
1. 사용자: "장비-001의 이력과 다음 점검은?"

2. LLM 분석:
   maintenance_history (0.92) ✅
   → 1개 Tool 선택
   → execution_order: sequential

3. Tool 실행:
   Task: maintenance_history({equipment_id: "1"})
   ├─ Source: primary_postgres
   └─ Result: [{date: "2026-01-20", type: "정기점검"},
               {date: "2026-01-15", type: "부품교체"}]

4. 답변:
   "장비-001의 최근 점검 이력:
    - 2026-01-20: 정기점검
    - 2026-01-15: 부품교체
    다음 정기점검: 2026-02-20 예정"
```

---

## 📝 정리

### Tool Asset의 역할
- Tool의 **정의**와 **설명** 제공
- LLM이 이 설명을 읽고 **적합한 Tool 선택**
- Tool의 **구성 방식** (database_query, http_api 등) 정의
- 실행 시 필요한 **파라미터 스키마** 정의

### Source Asset의 역할
- Tool이 데이터를 가져올 **데이터소스 연결 정보** 제공
- DB, API, Graph DB 등의 **물리적 연결 정보**
- Tool의 `source_ref`가 이를 참조

### 다른 Asset의 역할
- Query Asset: 복잡한 쿼리 저장 (선택)
- Mapping Asset: 키워드 기반 선택 (LLM 없을 때)
- Prompt Asset: 불필요 (내장 프롬프트)
- Schema Asset: 불필요 (Tool 스키마로 충분)

### 최종 결론
**"Tool Asset + Source Asset이면 완전한 오케스트레이션 가능!"**

나머지 Asset들은 **특정 도메인이나 고급 기능**을 위한 선택사항입니다.
