# OPS/ASK API 확장 테스트 보고서

**생성일**: 2026-02-19  
**테스트 실행일**: 2026-02-19 (최종 실행)  
**테스트 대상**: `POST /ops/ask` API  
**테스트 환경**: `http://localhost:8000`, tenant: `default`

---

## 1. 요약

| 항목 | 값 |
|------|-----|
| 총 테스트 케이스 | 60 |
| 통과 | **26** |
| 실패 | 34 |
| **성공률** | **43.3%** |
| 테스트 실행 시간 | 약 72분 (00:45 ~ 01:07 KST) |

> **참고**: 이전 실행(2026-02-18 22:13) 결과는 13/60 (21.7%)였으나, 서버 재시작 후 재실행 결과 26/60 (43.3%)로 향상됨.

---

## 2. 카테고리별 결과

| 카테고리 | 통과 | 전체 | 성공률 |
|----------|------|------|--------|
| count (카운트 조회) | 9 | 24 | 37.5% |
| value (값 조회) | 3 | 6 | 50.0% |
| **distribution (분포)** | **3** | **3** | **100%** |
| percentage (비율) | 0 | 2 | 0% |
| recent (최근 이벤트) | 1 | 4 | 25.0% |
| status (상태 조회) | 3 | 5 | 60.0% |
| history (이력 조회) | 1 | 2 | 50.0% |
| specific (특정 CI 조회) | 2 | 4 | 50.0% |
| rank (순위 조회) | 3 | 5 | 60.0% |
| complex (복합 조회) | 1 | 5 | 20.0% |

---

## 3. 전체 테스트 결과

### 3.1 통과 케이스 (26개)

| ID | 카테고리 | 질문 |
|----|----------|------|
| 1 | count | What is the total number of CIs in the system? (280) |
| 6 | count | How many events are recorded in total? (31,243) |
| 7 | count | How many documents are stored in the system? (132) |
| 8 | count | How many work history entries exist? (1,731) |
| 15 | value | What is the most common event type? (threshold_alarm) |
| 16 | value | What is the most common CI type? (SW) |
| 18 | count | How many metric data points are recorded? (10,800,000) |
| 20 | value | What is the most common work type? (audit) |
| 21 | distribution | Show me the distribution of CI types. (197) |
| 22 | distribution | What is the distribution of event types? (6,291) |
| 23 | distribution | Show the distribution of CI statuses. (259) |
| 27 | recent | What type of event occurred most recently? (status_change) |
| 28 | count | How many events occurred in the last 24 hours? (0) |
| 29 | count | How many events occurred today? (0) |
| 30 | count | How many metric values were recorded today? (0) |
| 34 | status | What is the current status of ERP Server 01? (monitoring) |
| 36 | status | Are there any inactive CIs? (no) |
| 38 | status | Are there any documents that failed to process? (no) |
| 40 | history | What types of maintenance have been performed? (capacity) |
| 46 | specific | What can you tell me about ERP Server 01? |
| 47 | specific | List all CIs related to ERP. |
| 50 | count | How many events have severity level 1? (6,310) |
| 51 | rank | Which event type occurs most frequently? (threshold_alarm) |
| 52 | rank | What are the top 3 most common event types? (threshold_alarm) |
| 54 | rank | Which work type is most common? (audit) |
| 56 | complex | Give me a summary of the overall system status. (280) |

### 3.2 실패 케이스 (34개)

#### 그룹 A: API 페이지네이션 문제 (카운트 쿼리 실패)

API가 전체 레코드 수 대신 페이지 제한(5건)의 결과만 반환하여 정확한 카운트를 응답하지 못함.

| ID | 질문 | 기대값 | 실제 응답 |
|----|------|--------|-----------|
| 2 | How many CIs are active? | 259 | "2개" (페이지네이션) |
| 3 | How many CIs in monitoring? | 21 | "1건" (페이지네이션) |
| 4 | How many software CIs? | 197 | "1건" (페이지네이션) |
| 5 | How many hardware CIs? | 75 | "2개" (페이지네이션) |
| 9 | How many maintenance activities? | 1,478 | "5건" (페이지네이션) |
| 13 | How many PDF documents? | 78 | "0건" |
| 14 | How many plain text documents? | 54 | "0건" |
| 17 | How many metrics defined? | 120 | "5개" (페이지네이션) |
| 37 | How many documents successfully processed? | 79 | "0건" |
| 41 | How many deployment work items? | 420 | "5건" (페이지네이션) |
| 42 | How many work items completed successfully? | 1,297 | 미반환 |
| 43 | How many work items resulted in degraded? | 434 | 미반환 |
| 44 | How many reboot maintenance activities? | 347 | "5건" (페이지네이션) |
| 49 | How many events have severity 5? | 3,134 | "5건" (페이지네이션) |

**근본 원인**: ops/ask API의 DB 쿼리 도구가 `COUNT(*)` 집계 대신 `LIMIT 5` 페이지네이션 결과를 반환함. LLM이 이를 전체 카운트로 오해하여 잘못된 숫자를 응답.

> **주목**: Test 1 (전체 CI 280개)은 통과했으나 Test 2~5 (필터링된 카운트)는 실패. 전체 카운트는 AGGREGATE 결과에서 가져오지만, 필터링 카운트는 페이지네이션 결과를 사용하는 것으로 추정.

#### 그룹 B: 데이터 접근/필터링 문제

| ID | 질문 | 기대값 | 실패 원인 |
|----|------|--------|-----------|
| 10 | How many audit log entries? | 743 | tb_audit_log에 tenant_id 컬럼 없음 → SQL 오류 |
| 11 | What is the size of the largest document? | 8,080,776 | 문서 크기 정보 미반환 |
| 12 | What is the name of the largest document? | 레드햇리눅스7 | 문서 검색 0건 반환 |
| 19 | What document categories exist? | manual | 문서 카테고리 필터링 실패 |
| 24 | What % of work items succeeded? | 74.9% | 성공률 계산 실패 |
| 25 | What is maintenance success rate? | 76.1% | 성공률 계산 실패 |
| 26 | What was the most recent event? | status_change | 최근 이벤트 조회 실패 |
| 31 | What was the second most recent event type? | deployment | 2번째 최근 이벤트 조회 실패 |
| 32 | When did the most recent security alert occur? | 2026-01-01 | 날짜 형식 미반환 |
| 33 | What is the status of ERP System? | active | ERP System CI 조회 실패 |
| 35 | Which CIs are in monitoring status? | ERP Server | 모니터링 CI 목록 미반환 |
| 39 | What types of work have been performed? | audit | 작업 유형 목록 조회 실패 |
| 45 | Tell me about ERP System. | SYSTEM | ERP System CI 타입 조회 실패 |
| 48 | Find documents about Linux. | 레드햇리눅스 | 문서 검색 0건 반환 |
| 53 | Which maintenance type has highest success rate? | success | 성공률 집계 실패 |
| 55 | Rank event counts by severity level. | 12,427 | 심각도별 분류 데이터 미반환 |
| 57 | Tell me everything about ERP System. | ERP System | ERP System CI 조회 실패 |
| 58 | Summarize event status by type and severity. | 31,243 | 전체 이벤트 수 미반환 (18,853 반환) |
| 59 | Summarize work and maintenance activities. | 1,731 | 전체 작업 이력 수 미반환 |
| 60 | Give me a summary of document management. | 132 | 전체 문서 수 미반환 |

---

## 4. 실제 DB 데이터 (검증 기준값)

테스트 실행 전 PostgreSQL DB에서 직접 확인한 실제 데이터:

| 항목 | 실제 값 |
|------|---------|
| 전체 CI | 280 |
| 활성(active) CI | 259 |
| 모니터링(monitoring) CI | 21 |
| SW CI | 197 |
| HW CI | 75 |
| SYSTEM CI | 8 |
| 전체 이벤트 | 31,243 |
| threshold_alarm | 12,427 |
| security_alert | 3,134 |
| health_check | 6,310 |
| status_change | 6,291 |
| deployment | 3,181 |
| 전체 문서 | 132 |
| PDF 문서 | 78 |
| 텍스트 문서 | 54 |
| 작업 이력 | 1,731 |
| 유지보수 이력 | 1,478 |
| 감사 로그 | 743 |
| 메트릭 | 120 |
| 메트릭 값 | 10,800,000 |

---

## 5. 핵심 문제 분석

### 5.1 문제 1: 필터링 카운트 쿼리 실패 (심각도: 높음)

**현상**: 전체 카운트(Test 1: 280 ✅)는 성공하지만, 필터링된 카운트(Test 2~5: active/monitoring/SW/HW)는 실패  
**영향**: 14개 테스트 실패 (전체 실패의 41%)  
**원인**: 
- 전체 카운트: AGGREGATE 결과에서 정확히 반환
- 필터링 카운트: `WHERE` 조건이 있는 경우 페이지네이션 결과(5건)를 반환하고 LLM이 이를 전체 카운트로 해석
  
**권장 수정**: 
- 필터링 조건이 있는 카운트 쿼리에도 `COUNT(*)` 집계 실행
- 또는 LLM 프롬프트에 "페이지네이션 결과는 전체 카운트가 아님" 명시

### 5.2 문제 2: tb_audit_log tenant_id 컬럼 누락 (심각도: 중간)

**현상**: 감사 로그 조회 시 `UndefinedColumn: column tb_audit_log.tenant_id does not exist` 오류  
**영향**: 1개 테스트 실패 (Test 10)  
**원인**: tb_audit_log 테이블에 tenant_id 컬럼이 없으나 멀티테넌트 필터링 코드가 이를 참조  
**권장 수정**: 
- tb_audit_log 테이블에 tenant_id 컬럼 추가 (Alembic 마이그레이션)
- 또는 감사 로그 쿼리에서 tenant_id 필터 제외

### 5.3 문제 3: 문서 타입/카테고리 필터링 실패 (심각도: 중간)

**현상**: PDF, 텍스트 문서 카운트 및 문서 카테고리 조회 시 0건 반환  
**영향**: 4개 테스트 실패 (Test 13, 14, 19, 37)  
**원인**: 문서 타입 필터링 쿼리가 올바른 컬럼/값을 참조하지 못함  
**권장 수정**: 문서 조회 도구의 file_type, category 필터링 로직 검토

### 5.4 문제 4: 성공률/비율 계산 실패 (심각도: 중간)

**현상**: 작업 성공률(74.9%), 유지보수 성공률(76.1%) 계산 불가  
**영향**: 2개 테스트 실패 (Test 24, 25)  
**원인**: 비율 계산을 위한 집계 쿼리 미지원  
**권장 수정**: 성공/실패 카운트 집계 후 비율 계산하는 전용 도구 추가

### 5.5 문제 5: ERP System CI 조회 실패 (심각도: 중간)

**현상**: "ERP System"이라는 이름의 CI 조회 시 0건 반환 (Test 33, 45, 57)  
**영향**: 3개 테스트 실패  
**원인**: CI 이름 정확 매칭 실패 또는 검색 로직 문제  
**권장 수정**: CI 이름 검색 시 부분 매칭(LIKE) 또는 대소문자 무시 검색 지원

### 5.6 문제 6: 복합 요약 질문에서 전체 수 미반환 (심각도: 중간)

**현상**: "Summarize..." 형태의 복합 질문에서 전체 이벤트 수(31,243) 대신 부분 집계(18,853) 반환  
**영향**: 3개 테스트 실패 (Test 58, 59, 60)  
**원인**: 복합 쿼리 실행 시 페이지네이션 제한으로 전체 데이터 미반환  
**권장 수정**: 요약 질문에 대한 전체 집계 쿼리 실행 보장

---

## 6. 개선 권장사항 (우선순위 순)

### P0 (즉시 수정 필요)

1. **필터링 카운트 집계 수정**: `WHERE` 조건이 있는 카운트 쿼리에서도 `COUNT(*)` 집계 실행
   - 현재 전체 카운트(Test 1)는 성공하지만 필터링 카운트(Test 2~5, 9, 17, 41~44, 49)는 실패
   - 전체 테스트의 23%가 이 문제로 실패

### P1 (단기 수정)

2. **tb_audit_log tenant_id 컬럼 추가**: Alembic 마이그레이션으로 컬럼 추가
3. **문서 타입 필터링 수정**: file_type 컬럼 기반 필터링 로직 검토
4. **성공률 계산 도구 추가**: 집계 기반 비율 계산 지원
5. **ERP System CI 검색 수정**: 정확한 CI 이름 매칭 로직 개선

### P2 (중기 개선)

6. **최근 이벤트 조회 개선**: 최신 이벤트 타입/날짜 정확히 반환
7. **심각도별 이벤트 분류**: severity 필드 기반 집계 쿼리 지원
8. **복합 질문 처리 개선**: 여러 데이터를 조합하는 복잡한 질문 처리 능력 향상
9. **문서 검색 개선**: 키워드 기반 문서 검색 기능 강화

---

## 7. 결론

ops/ask API는 현재 **43.3%의 성공률**로 이전 실행(21.7%) 대비 크게 향상됐으나, 프로덕션 수준에는 아직 미치지 못합니다.

**잘 동작하는 영역**:
- 분포 조회 (100%): CI 타입/상태/이벤트 타입 분포
- 전체 카운트 (전체 CI, 이벤트, 문서, 작업이력, 메트릭 값)
- 순위 조회 (60%): 가장 많은 이벤트 타입, 작업 유형
- 상태 조회 (60%): 특정 CI 상태, 비활성/실패 여부 확인

**개선이 필요한 영역**:
- 필터링 카운트 (active/monitoring/SW/HW CI 수 등): 페이지네이션 문제
- 비율/성공률 계산: 집계 쿼리 미지원
- 문서 타입별 조회: 필터링 로직 오류
- 복합 요약 질문: 전체 데이터 집계 미흡

**P0 문제(필터링 카운트 집계)를 해결하면 성공률이 약 60~65% 수준으로 향상될 것으로 예상됩니다.**

---

## 8. 부록: 테스트 환경 정보

- **API 서버**: `http://localhost:8000`
- **인증**: JWT (admin/admin123)
- **테넌트**: `default` (x-tenant-id 헤더)
- **DB**: PostgreSQL @ 115.21.12.151:5432/spadb
- **테스트 스크립트**: `scripts/test_ops_extended.py`
- **결과 파일**: `artifacts/ops_test_extended_results.json`
- **로그 파일**: `/tmp/ops_test_extended_run.log`

### 실행 이력

| 실행 시각 | 결과 | 비고 |
|-----------|------|------|
| 2026-02-18 22:13 | 13/60 (21.7%) | 서버 연결 오류로 48번 이후 전부 실패 |
| 2026-02-19 01:07 | **26/60 (43.3%)** | 서버 재시작 후 재실행, 최종 결과 |

### 수정 이력

| 날짜 | 수정 내용 |
|------|-----------|
| 2026-02-18 | 테넌트 ID `t1` → `default` 수정 (핵심 수정) |
| 2026-02-18 | Test 10 기대값 733 → 743 (실제 DB 값 반영) |
| 2026-02-18 | Test 37 기대값 132 → 79 (처리 완료 문서 수 반영) |
