# 🔴 시스템 진단: Query Assets이 실행되지 않음

**작성일**: 2026-01-29
**진단 결과**: ❌ **CRITICAL - Query Assets 미실행**

---

## 문제 설명

### 실제 DB 데이터
```
ci                : 280 rows
event_log         : 31,243 rows
metrics           : 120 rows
metric_value      : 10,800,000 rows
tb_audit_log      : 667 rows
```

### API 응답 결과
```
모든 쿼리: "0건" 반환
```

### 원인
**Query Assets이 시스템에서 실행되지 않고 있음**

---

## 근거

### Test 1: "What is the current system status? Tell me the total number of CIs"
- **DB 실제 데이터**: 280 CI
- **API 응답**: "0건"
- **예상**: 280을 포함한 답변
- **실제**: "PRIMARY 및 UNKNOWN 값이 비어 있습니다"

### Test 3: "How many events are recorded in the system?"
- **DB 실제 데이터**: 31,243 events
- **API 응답**: "0건"
- **예상**: 31,243을 포함한 답변
- **실제**: "기록된 이벤트가 존재하지 않아 0건"

### Test 7: "How many metric data points are recorded?"
- **DB 실제 데이터**: 10,800,000 metric values
- **API 응답**: "0건"
- **예상**: 10,800,000을 포함한 답변
- **실제**: "메트릭 데이터 포인트는 0개"

---

## 기술적 원인

### 생성된 Query Assets
- ✅ 20개 Query Asset 생성됨 (schema_json에 SQL 포함)
- ✅ Query Asset Registry 구현됨
- ✅ DynamicTool 구현됨
- ✅ ToolExecutor.execute_tool() 메서드 추가됨

### 실행되지 않는 이유
1. **Tool Registry가 중복 제거함**
   - 12개 도구 모두 tool_type = "database_query"
   - Registry가 tool_type으로 key를 저장
   - 첫 번째 도구만 저장, 나머지 11개는 버려짐

2. **Query Asset 선택 로직이 없음**
   - Keywords 매칭 미구현
   - CI 그래프 쿼리가 하드코딩됨
   - Query Asset으로 라우팅하는 메커니즘 부재

3. **Stage Executor가 여전히 legacy 도구 호출**
   - `tool_executor.execute_tool(tool_type="ci_lookup")` ← 하드코딩
   - `tool_executor.execute_tool(tool_type="ci_aggregate")`
   - 실제 Query Asset으로 라우팅되지 않음

---

## 해결 방안

### 즉시 필요한 수정 (우선순위 1)

1. **Tool Registry 변경**: tool_type이 아닌 도구 이름으로 등록
   ```python
   # 현재 (잘못됨)
   registry.register_dynamic(tool)  # tool.tool_type으로 등록

   # 수정해야 함
   registry.register_dynamic(tool)  # tool.name으로 등록
   ```

2. **Query Asset 선택 로직 구현**
   - 질문 keywords 추출
   - Query Asset 메타데이터와 매칭
   - 적절한 Query Asset 선택

3. **Stage Executor 수정**
   - 하드코딩된 tool_type 제거
   - Query Asset Selector로 라우팅
   - 실제 쿼리 실행

### 예상 결과 (수정 후)

```
Test 1: "What is the current system status?"
  Before: "0건"
  After: "There are 280 CIs in the system"  ✅

Test 3: "How many events are recorded?"
  Before: "0건"
  After: "There are 31,243 events recorded"  ✅
```

---

## 결론

- **현 상태**: 10% 통과율 (2/20)
- **근본 원인**: Query Assets이 선택/실행되지 않음
- **해결 난이도**: 중간 (2-3시간)
- **필요한 작업**: Tool registry 수정 + Query Asset selector 구현

---

**다음 단계**: Tool Registry 구조 변경 및 Query Asset Selector 구현
