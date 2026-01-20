# OPS CI API 테스트 실패 원인 분석 및 수정 계획

**생성일**: 2026-01-20
**상태**: 핵심 문제 파악 완료, 수정 코드 준비 중

---

## 1. 핵심 문제 3가지

### 문제 1: 명시 CI코드 입력 시에도 "Multiple candidates found" 반환
**증상**:
- 질의: "srv-erp-01의 상태를 알려줘."
- 예상: CI details/tags/attributes 테이블
- 실제: "Multiple candidates found" + 10개 앱 리스트

**원인**:
```
ci_resolver.py의 3단계 검색 전략:
1단계: 정확코드 매칭 (srv-erp-01) → 찾음 ✓
2단계: ci_code 패턴 (ILIKE '%erp%') → 10개 앱 찾음 (app-erp-alert-*, app-erp-order-*, ...)
3단계: ci_name 패턴 → 추가

→ 1단계 결과 우선도(1.0)가 높지만, limit=5 제한으로 일부만 반환되면 candidates=[srv-erp-01, app-erp-alert-04-2, ...]
→ runner의 _handle_lookup_async()에서 len(candidates) > 1 판정 후 _find_exact_candidate() 호출
→ _find_exact_candidate()는 "srv-erp-01" ∈ candidates && identifier "srv-erp-01"인지 확인
→ 일치하면 정확 매칭 성공 → 상세조회로 가야 함

BUT: 2단계 검색이 너무 광범위 (ILIKE '%erp%'는 모든 erp 관련 CI 반환)
```

**근본원인**:
- `ci_resolver.py`가 3단계 모두 실행 (limit=5씩)
- 정확코드가 있으면 1단계만 반환하고 2/3단계 스킵 필요
- `_handle_lookup_async()` line 2119의 `_find_exact_candidate()`가 정확히 작동하나, 2/3단계 candidates 누적이 우선도를 흐림

**해결방법**:
```python
# ci_resolver.py: resolve_ci() 수정
def resolve_ci(question: str, tenant_id: str = "t1", limit: int = 5) -> list[CIHit]:
    codes = _extract_codes(question)  # "srv-erp-01" 추출
    hits: list[CIHit] = []

    if codes:
        # 명시 코드가 있으면 정확코드만 검색 (2/3단계 스킵)
        for code in codes:
            exact_hits = _query_exact(code, tenant_id, limit)
            hits.extend(exact_hits)

        # 정확코드 검색 결과가 있으면 즉시 반환 (2/3단계 생략)
        if hits:
            return hits[:limit]

        # 정확코드 검색 실패 → broad search는 금지 (no-data 반환할 것)
        # 즉, 명시 코드가 있는데 찾지 못하면 빈 리스트 반환
        return []

    # 명시 코드 없으면 기존 3단계 검색 진행 (일반 질의)
    # ... (2/3단계 로직)
```

---

### 문제 2: 존재하지 않는 CI(srv-erp-99)에서도 "Multiple candidates found" 반환
**증상**:
- 질의: "srv-erp-99의 상태를 알려줘."
- 예상: "찾을 수 없음" 안내 블록
- 실제: "Multiple candidates found" + 후보 리스트

**원인**:
```
1. ci_resolver가 "srv-erp-99" 추출 → 정확코드 검색
2. srv-erp-99는 DB에 없음 (seed_ci.py에서 srv-erp-01, srv-erp-02, ... 생성)
3. 1단계 결과 0건 → 2단계 "ci_code ILIKE '%erp%'" 검색 → 10개 앱 반환
4. candidates = [app-erp-alert-*, app-erp-order-*, ...]
5. _find_exact_candidate(candidates, ["srv-erp-99"]) → 불일치
6. → "Multiple candidates found" 반환 (잘못됨)
```

**근본원인**:
- 명시 코드(srv-erp-99)가 추출되었는데도 2/3단계 broad search로 폴백
- 명시 코드는 정확 매칭만 수행 + 실패 시 no-data 반환해야 함

**해결방법**: 문제 1 해결과 동일 (resolve_ci() 수정)

---

### 문제 3: Metric/History 질문이 후보 리스트로 끝남
**증상**:
- 질의: "srv-erp-01 서버의 2025-12-01부터 2025-12-31까지 CPU 사용률 평균값과 최종 값을 보여줘."
- 예상: CPU 그래프/수치 + 평균/최종값 표
- 실제: "Multiple candidates found" + 앱 리스트

**원인**:
```
1. Planner: "CPU 사용률 평균값" → METRIC_KEYWORDS 포함 확인 → metric_spec 생성 ✓
2. Planner: plan.intent = Intent.AGGREGATE, plan.metric = MetricSpec(...) ✓
3. Runner: _run_auto_recipe_async() 호출 (plan.mode == AUTO이고 metric 있을 때)
   또는 _handle_lookup_async() 호출 (plan.mode == CI)
4. Runner: _handle_lookup_async()에서 ci.search 호출
   → candidates = [srv-erp-01, app-erp-alert-*, app-erp-order-*, ...]
5. 위와 동일하게 "Multiple candidates found" 반환
```

**근본원인**:
- 명시 CI코드(srv-erp-01) 추출 후 정확 매칭 성공해야 metric executor로 이동
- 그 전에 resolver의 broad search가 다른 CI 포함

**해결방법**: 문제 1/2 해결 후, runner의 라우팅 강화 필요
```python
# runner.py: _handle_lookup_async() 수정
if len(candidates) == 1:
    # 단일 CI로 확정 → metric/history 실행으로 라우팅
    ci_id = candidates[0]["ci_id"]
    if self.plan.metric:
        return await self._handle_metric_async(ci_id)
    elif self.plan.history.enabled:
        return await self._handle_history_async(ci_id)
    else:
        return await self._ci_get_async(ci_id)  # CI 상세조회

elif len(candidates) > 1:
    # 다중 후보 → 정확 매칭 시도
    exact = _find_exact_candidate(candidates, search_keywords)
    if exact:
        ci_id = exact["ci_id"]
        if self.plan.metric:
            return await self._handle_metric_async(ci_id)
        # ... (history 등)
    # 정확 매칭 실패 → 후보 리스트 반환 (Ambiguous case 처리)
```

---

## 2. 부차 문제 (비교적 쉬운 수정)

### 문제 4: time_range 파싱 미흡 (범위 지정 미지원)
**현재**: "2025-12-01부터 2025-12-31까지" → ISO_DATE_PATTERN에서 "2025-12-01"만 추출
**필요**: "2025-12-01"과 "2025-12-31" 모두 파싱 → TimeRange(start=..., end=...)

**수정 위치**: `time_range_resolver.py` → `_parse_explicit_date_range()` 함수 추가
```python
# 범위 날짜 패턴: "YYYY-MM-DD부터 YYYY-MM-DD까지", "YYYY-MM-DD ~ YYYY-MM-DD"
RANGE_PATTERN = re.compile(
    r"(\d{4})[-년/.](\d{1,2})[-월/.](\d{1,2})(?:부터|부터|에서).*?(\d{4})[-년/.](\d{1,2})[-월/.](\d{1,2})(?:까지|항까지)",
)
```

---

### 문제 5: References 0건 (근거 정보 미기록)
**현재**: blocks에서 "references" 타입 추출 → 대부분 0건
**필요**: 각 executor(lookup, metric, history)가 실행 결과와 함께 references 기록

**수정 위치**:
1. `response_builder.py`: metric/history 결과 생성 시 references 블록 포함
2. `runner.py`: _handle_metric_async(), _handle_history_async() → references 기록
   ```python
   # 예: metric 실행 후
   self.references.append({
       "kind": "ci_metric",
       "payload": {
           "ci_id": ci_id,
           "ci_code": ci_code,
           "metric_key": "cpu_usage",
           "time_range": {"start": "2025-12-01", "end": "2025-12-31"},
       }
   })
   ```

---

### 문제 6: OPS_MODE 미기록
**현재**: trace/meta에 ops_mode 필드 없음
**필요**: meta/trace에 "ops_mode": "real" 또는 "auto" 기록

**수정 위치**: `runner.py` line 969-979 (meta 생성)
```python
meta = {
    "route": "ci",
    "ops_mode": self.plan.mode.value,  # "ci" 또는 "auto"
    ...
}
```

---

### 문제 7: Depth 요청 미반영 (requested_depth ≠ 사용자 요청)
**현재**: "depth 10으로 확장해줘" → trace["policy_decisions"]["requested_depth"] = 2 (고정)
**필요**: 사용자 요청에서 depth 추출 → requested_depth = 10 저장

**수정 위치**: `planner_llm.py` 또는 `graph_resolver.py`
```python
# 질문에서 depth 추출
depth_match = re.search(r"depth\s+(\d+)", question)
if depth_match:
    requested_depth = int(depth_match.group(1))
else:
    requested_depth = 1  # 기본값
plan.graph.depth = requested_depth
```

---

## 3. 테스트 스펙 강화 (강화 사항)

### A. Lookup - 명시 CI코드
```python
question = "srv-erp-01의 현재 상태와 기본 정보를 알려줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks 존재
# 3. blocks에 "CI details" table 또는 ci_code=="srv-erp-01" 확인
# 4. NO "Multiple candidates found" (명시 코드는 후보 금지)
# 5. trace.references >= 1
# 6. ops_mode 기록됨
```

### B. Metric - 명시 CI코드 + metric 질문
```python
question = "srv-erp-01 서버의 2025-12-01부터 2025-12-31까지 CPU 사용률 평균값과 최종 값을 보여줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 metric 결과 (그래프/수치/테이블 포함, "Multiple candidates" 금지)
# 3. trace.references에 ci_code="srv-erp-01", metric_key="cpu_usage", time_range 포함
# 4. trace["plan_validated"]["intent"] == "AGGREGATE"
```

### C. History - 명시 CI코드 + history 질문
```python
question = "srv-erp-01의 2025-12-01~2025-12-31 severity 2 이상 이벤트를 요약해줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 history 결과 (이벤트 요약/테이블, "Multiple candidates" 금지)
# 3. trace.references에 ci_code="srv-erp-01", event_type, severity 포함
```

### D. List - seed 기반 실제 필터
```python
# 현재: location=zone-a status=active → 0건 (seed에 없는 필터)
# 변경: seed DB 확인 후 실제 존재하는 필터 자동 선택
# 예: location=zone-a (seed에 존재) → rows >= 1

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 결과 테이블 (row >= 1 또는 "No matches" 정확한 안내)
```

### E. Multi-step - app 이력 + 호스트
```python
question = "app-erp-alert-04-2의 2025-12-01~2025-12-31 작업/배포 이력과 구동 호스트를 함께 보여줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 app 상세 + history 결과 (후보 금지)
# 3. graph/host 관련 정보 포함
```

### F. No-data - 존재하지 않는 CI
```python
question = "srv-erp-99의 상태를 알려줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 "찾을 수 없음" 또는 "No matches" 안내 텍스트
# 3. "Multiple candidates found" 금지 (치명적)
# 4. trace 포함
```

### G. Ambiguous - 모호한 질의
```python
question = "integration 앱의 최근 배포 상태를 알려줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 "Multiple candidates" 또는 disambiguation 인터페이스
# 3. next_actions에 선택 옵션 포함
# 4. (추가) 2-step 흐름: 사용자가 선택 후 재요청 → 최종 결과
```

### H. Policy - Depth 요청
```python
question = "app-erp-alert-04-2 영향 그래프를 depth 10으로 확장해줘."

# PASS 조건:
# 1. HTTP 200 + code == 0
# 2. blocks에 그래프/네트워크 시각화
# 3. trace["plan_validated"]["policy_decisions"]["requested_depth"] == 10
# 4. trace["plan_validated"]["policy_decisions"]["clamped_depth"] 기록 (정책 제한 있으면)
# 5. "Multiple candidates" 금지
```

---

## 4. 수정 순서 (우선도)

1. **P0**: ci_resolver.py - 명시 코드 시 broad search 차단
   - 영향: 문제 1, 2, 3 모두 해결
   - 시간: ~15분

2. **P1**: runner.py - 단일 CI 확정 후 metric/history 라우팅 강화
   - 영향: metric/history 질문 정상 처리
   - 시간: ~20분

3. **P2**: references 기록 추가
   - 영향: 근거 정보 기록
   - 시간: ~15분

4. **P3**: time_range 범위 파싱 + depth 추출 + ops_mode 기록
   - 영향: 메타데이터 완성
   - 시간: ~15분

5. **P4**: 테스트 코드 강화 + TEST_REPORT.md 재생성
   - 영향: 명확한 합격/불합격 기준
   - 시간: ~30분

---

## 5. 산출물 체크리스트

- [ ] 수정된 ci_resolver.py (P0)
- [ ] 수정된 runner.py (P1, P2, P3 부분)
- [ ] 수정된 planner_llm.py (depth/ops_mode)
- [ ] 수정된 time_range_resolver.py (범위 파싱)
- [ ] 강화된 test_ops_ci_ask_api.py (PASS 조건 명시)
- [ ] 새 TEST_REPORT.md (실제 결과, 합격 이유)
- [ ] 이 DEBUG_NOTES.md

---

**다음 단계**: 수정 코드 작성 시작
