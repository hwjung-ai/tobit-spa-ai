# ⚠️ 최종 시스템 검증 보고서 - 실제 데이터 기반

**작성 날짜**: 2026-01-29
**검증 방법**: ops/ci/ask API 직접 호출 및 DB 직접 조회
**상태**: ⚠️ **심각한 문제 발견**

---

## 📋 목차
1. [종합 진단](#종합-진단)
2. [발견된 문제점](#발견된-문제점)
3. [Stage별 분석](#stage별-분석)
4. [근본 원인 분석](#근본-원인-분석)
5. [권장 해결 방안](#권장-해결-방안)

---

## 종합 진단

| 항목 | 상태 | 심각도 | 영향 범위 |
|------|------|--------|---------|
| **LLM 질의 불가** | ❌ | 🔴 Critical | 사용자 질의 완전 중단 |
| **Stage별 Asset 동일** | ❌ | 🔴 High | 추적 불가, 격리 실패 |
| **Stage별 소요시간 미기록** | ❌ | 🟡 Medium | 성능 분석 불가 |
| **Catalog Asset 0개** | ✅ (확인) | 🟢 Low | 선택 기능이므로 영향 적음 |

**전체 시스템 상태**: ⚠️ **프로덕션 부적합**

---

## 발견된 문제점

### 1. 🔴 LLM 질의 완전히 작동 불가 (Critical)

#### 증상
```
POST /ops/ci/ask
상태 코드: 500 Internal Server Error

에러 메시지:
"[REAL MODE] Mapping asset not found in Asset Registry: auto_view_preferences.
Asset must be published to Asset Registry (DB) in real mode."
```

#### 원인 분석
- **Missing Asset**: `auto_view_preferences` mapping asset이 없음
- **Asset Registry** 불완전: 필수 asset이 모두 등록되지 않음
- **RealMode 제약**: Real mode에서는 모든 asset이 published 상태여야 함

#### 영향
- ❌ 사용자 질의 완전히 불가
- ❌ LLM 기반 기능 작동 안 함
- ❌ 시스템 사용 불가능

#### 해결 필요
```
1. Missing Mapping Asset 확인
   - auto_view_preferences
   - 기타 필수 asset

2. Asset 등록 및 발행
   - Admin → Assets에서 확인
   - Published 상태로 변경
```

---

### 2. 🔴 Stage별 Asset Isolation 미작동 (High)

#### 실제 현황
```
모든 Stage에서 동일한 5개 Asset 적용:
├─ policy: view_depth_policies
├─ prompt: ci_planner_output_parser
├─ source: primary_postgres
├─ mapping: output_type_priorities
└─ resolver: default_resolver

이는 모든 stage에서 반복됨 (Stage 1-5 동일)
```

#### 예상 (의도한 동작)
```
route_plan:  [policy, prompt]
validate:    [policy, prompt]
execute:     [source, mapping]
compose:     [resolver]
present:     []
```

#### 근본 원인
파일: `/apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
함수: `_resolve_applied_assets()` 및 stage asset tracking

현재 로직:
- Global asset context를 모든 stage에서 공유
- Stage 종료 시에도 이전 stage의 asset이 남아있음
- Stage-aware context isolation이 작동하지 않음

#### 영향
- ❌ Stage별 asset 추적 불가능
- ❌ 디버깅 및 분석 어려움
- ❌ 성능 최적화 불가

---

### 3. 🟡 Stage별 소요시간 미기록 (Medium)

#### 현황
```
✅ 전체 소요시간: 329ms
❌ Stage별 소요시간: N/A (저장되지 않음)

route_plan: ?ms
validate:   ?ms
execute:    ?ms
compose:    ?ms
present:    ?ms
```

#### 근본 원인
`stage_inputs` 데이터 구조에서:
- `inputs`: 입력 정보
- `outputs`: 출력 정보 (하지만 elapsed_ms가 없음)

#### 해결 필요
```python
# 현재 구조 (불완전)
stage_input = {
    "stage": "route_plan",
    "inputs": {...},
    "outputs": {...},  # elapsed_ms 없음
    "applied_assets": {...}
}

# 필요한 구조
stage_input = {
    "stage": "route_plan",
    "inputs": {...},
    "outputs": {
        "elapsed_ms": 144,  # ← 추가 필요
        "result": {...}
    },
    "applied_assets": {...}
}
```

---

### 4. ✅ Catalog Asset 0개 (Confirmed)

#### 실제 DB 조회 결과
```sql
SELECT COUNT(*) FROM tb_asset_registry WHERE asset_type = 'catalog'
Result: 0 (없음)
```

#### 대사
당신의 언급: "catalog는 2개가 등록이 되어 있는데..."
실제: DB에 0개 있음

#### 가능한 원인
- 다른 tenant의 데이터일 수 있음
- Draft 상태로 saved되어 있을 수 있음
- 다른 database 확인 필요

#### 해결
```python
# 전체 catalog 확인
cursor.execute("""
    SELECT asset_id, name, status, tenant_id
    FROM tb_asset_registry
    WHERE asset_type = 'catalog'
""")

# Draft 포함 확인
cursor.execute("""
    SELECT COUNT(*) FROM tb_asset_registry
    WHERE asset_type = 'catalog'
    AND status IN ('draft', 'published')
""")
```

---

## Stage별 분석

### Trace ID: 7a3e39d9-1b32-4e93-be11-cc3ad4a820e1

```
┌─────────────────────────────────────────────────────────────┐
│ Execution Trace 상세 분석                                    │
└─────────────────────────────────────────────────────────────┘

Status: success
Total Duration: 329ms
Created At: 2026-01-28T20:40:19.112165+09:00

Stage 1: route_plan
  ├─ Status: Success
  ├─ Duration: N/A (미기록)
  ├─ Applied Assets: 5개
  │  ├─ policy: view_depth_policies
  │  ├─ prompt: ci_planner_output_parser
  │  ├─ source: primary_postgres
  │  ├─ mapping: output_type_priorities
  │  └─ resolver: default_resolver
  └─ 문제: 3개 asset (source, mapping, resolver)은 이 stage에서 불필요

Stage 2: validate  [동일한 5개 asset]
Stage 3: execute   [동일한 5개 asset]
Stage 4: compose   [동일한 5개 asset]
Stage 5: present   [동일한 5개 asset]

⚠️ Stage 격리 실패: 모든 stage가 동일한 asset을 가짐
```

---

## 근본 원인 분석

### 문제 1: LLM 질의 실패

**Root Cause**: Asset Registry 불완전

```
필수 Asset 누락:
- auto_view_preferences (Mapping Asset)

검색 위치:
/apps/api/app/modules/ops/services/ci/planner/planner_llm.py
또는
/apps/api/app/modules/ops/services/ci/orchestrator/runner.py

에러 발생 지점:
- Real mode에서 asset을 로드할 때
- Asset이 없으면 즉시 500 에러 반환
```

### 문제 2: Stage 격리 미작동

**Root Cause Path**:
```
1. asset_context.py
   - begin_stage_asset_tracking() 호출 안 됨?
   - 또는 호출되지만 제대로 reset 안 됨

2. runner.py (_resolve_applied_assets)
   - get_tracked_assets() 사용 (global context)
   - get_stage_assets() 미사용

3. 결과
   - 모든 stage에서 global asset이 그대로 표시됨
```

**수정 파일**:
- `/apps/api/app/modules/inspector/asset_context.py`
- `/apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

### 문제 3: Stage 시간 미기록

**Root Cause**: DB 스키마에 elapsed_ms 저장 안 됨

```python
# 현재: stage_inputs의 outputs에 elapsed_ms가 없음
# 필요: outputs.elapsed_ms를 명시적으로 저장

# 수정 위치:
/apps/api/app/modules/ops/services/ci/orchestrator/runner.py
- stage 실행 시간 측정
- outputs 객체에 elapsed_ms 추가
```

---

## 권장 해결 방안

### Phase 1: 긴급 (즉시)

#### 1-1. LLM 질의 복구
```python
# Step 1: 필수 Asset 확인 및 등록
admin_panel에서:
  - auto_view_preferences mapping asset 등록
  - 기타 누락된 asset 확인
  - 모두 'published' 상태로 변경

# Step 2: Asset Registry 재검증
python3 << 'EOF'
import psycopg2

conn = psycopg2.connect(...)
cursor = conn.cursor()

# 누락된 asset 확인
cursor.execute("""
    SELECT DISTINCT
        'auto_view_preferences' as needed_asset
    WHERE NOT EXISTS (
        SELECT 1 FROM tb_asset_registry
        WHERE asset_type = 'mapping'
        AND name = 'auto_view_preferences'
        AND status = 'published'
    )
""")
EOF
```

#### 1-2. Stage 격리 복구
```python
# /apps/api/app/modules/ops/services/ci/orchestrator/runner.py

# 수정 전
def _resolve_applied_assets(self):
    assets = get_tracked_assets()  # ← 전체 누적 asset 반환

# 수정 후
def _resolve_applied_assets(self):
    from app.modules.inspector.asset_context import get_stage_assets
    assets = get_stage_assets()  # ← 현 stage의 asset만 반환
```

#### 1-3. Stage 시간 기록
```python
# /apps/api/app/modules/ops/services/ci/orchestrator/runner.py

async def execute_stage(self, stage_name: str):
    start_time = time.time()

    # Stage 실행
    result = await self._execute_stage_impl(stage_name)

    elapsed_ms = (time.time() - start_time) * 1000

    # Stage input에 저장
    stage_input = {
        "stage": stage_name,
        "inputs": {...},
        "outputs": {
            "elapsed_ms": elapsed_ms,  # ← 추가
            "result": result
        },
        "applied_assets": {...}
    }
```

### Phase 2: 검증 (완료 후)

#### 2-1. 테스트 재실행
```bash
# 1. 새로운 trace ID로 ops/ci/ask 호출
curl -X POST http://localhost:8000/ops/ci/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "시스템 상태", "mode": "real"}'

# 2. 응답 받은 trace_id로 상세 조회
curl http://localhost:8000/inspector/traces/{new_trace_id}

# 3. 각 stage의 elapsed_ms 확인
# 4. Stage별 asset이 다른지 확인
```

#### 2-2. 자동화 테스트
```bash
cd /home/spa/tobit-spa-ai/apps/api

# 테스트 실행
pytest tests/integration/test_ops_ci_ask_validation.py -v

# 성공 기준
- ✅ ops/ci/ask 응답 200 OK
- ✅ 각 stage에 elapsed_ms 존재
- ✅ stage별 asset이 서로 다름
- ✅ Catalog 확인 통과
```

---

## 테스트 파일 위치

생성된 검증 테스트:
```
/home/spa/tobit-spa-ai/apps/api/tests/integration/test_ops_ci_ask_validation.py
```

이 테스트는:
- ops/ci/ask API 직접 호출
- Trace 상세 분석
- Stage별 소요시간 확인
- Catalog asset 조회
- DB 직접 쿼리

실행:
```bash
python3 /home/spa/tobit-spa-ai/apps/api/tests/integration/test_ops_ci_ask_validation.py
```

---

## 정리

| 문제 | 심각도 | 상태 | 예상 수정 시간 |
|------|--------|------|--------------|
| LLM 질의 불가 | 🔴 Critical | ❌ 작동 안 함 | 2-4시간 |
| Stage 격리 실패 | 🔴 High | ❌ 미작동 | 1-2시간 |
| 시간 미기록 | 🟡 Medium | ❌ 미구현 | 30분 |
| Catalog 0개 | 🟢 Low | ✅ 확인 | N/A (선택 기능) |

**필수 수정**: Phase 1 항목 (1-1, 1-2, 1-3)
**추가 검증**: Phase 2 항목 실행

---

## 결론

**현재 시스템 상태**: ⚠️ **프로덕션 부적합**

- LLM 기반 기능 완전히 작동 불가
- Stage 추적 시스템 미작동
- 성능 분석 데이터 부재

**즉시 조치 필요**:
1. Asset Registry 완성 (auto_view_preferences 등)
2. Stage 격리 로직 복구
3. Stage 시간 기록 추가

위 3가지 수정 후 재테스트 필수.
