# 📊 OPS_TEST_CASE_EXTENDED (60개) 테스트 결과 보고서

**실행일**: 2026-02-17 20:16:45 ~ 20:36:00 (약 20분 소요)
**모드**: 전체 (all)
**API**: http://localhost:8000

---

## 📈 전체 결과 요약

| 항목 | 값 |
|------|-----|
| 총 테스트 | 60 |
| 성공 | 15 |
| 실패 | 45 |
| **성공률** | **25.0%** |

---

## ✅ 성공한 테스트 (15개)

| ID | 질의 | 예상 답변 | 결과 |
|----|------|----------|------|
| 15 | What is the most common event type? | threshold_alarm | ✅ Found |
| 16 | What is the most common CI type? | SW | ✅ Found |
| 20 | What is the most common work type? | audit | ✅ Found |
| 21 | Show me the distribution of CI types. | 197 | ✅ Found |
| 29 | How many events occurred today? | 0 | ✅ Found |
| 30 | How many metric values were recorded today? | 0 | ✅ Found |
| 38 | Are there any documents that failed to process? | no | ✅ Found |
| 39 | What types of work have been performed? | audit | ✅ Found |
| 40 | What types of maintenance have been performed? | capacity | ✅ Found |
| 46 | What can you tell me about ERP Server 01? | ERP Server 01 | ✅ Found |
| 47 | List all CIs related to ERP. | ERP | ✅ Found |
| 51 | Which event type occurs most frequently? | threshold_alarm | ✅ Found |
| 52 | What are the top 3 most common event types? | threshold_alarm | ✅ Found |
| 56 | Give me a summary of the overall system status. | 280 | ✅ Found |
| 58 | Summarize the event status by type and severity. | 31,243 | ✅ Found |

---

## 📊 카테고리별 결과

| 카테고리 | 성공 | 실패 | 성공률 | 비고 |
|----------|------|------|--------|------|
| **history** | 2 | 0 | **100%** | 🏆 최고 |
| value | 3 | 3 | 50% | |
| specific | 2 | 2 | 50% | |
| rank | 2 | 3 | 40% | |
| complex | 2 | 3 | 40% | |
| distribution | 1 | 2 | 33% | |
| status | 1 | 4 | 20% | |
| **count** | 2 | 22 | **8.3%** | ⚠️ 개수 세기 문제 |
| percentage | 0 | 2 | 0% | ❌ |
| recent | 0 | 4 | 0% | ❌ |

---

## ❌ 실패한 주요 패턴 분석

### 1. 개수 세기 (count) 문제 - 22개 실패
- "How many CIs..." 형태의 질문에서 숫자가 정확히 반환되지 않음
- 예: "What is the total number of CIs in the system?" → 280이 응답에 포함되지 않음
- 원인: LLM이 집계 결과를 텍스트로 요약하면서 숫자가 누락되거나 다르게 표현됨

### 2. 최근/이전 (recent) 문제 - 4개 실패
- "most recent event", "second most recent" 등의 시간 관련 질문 실패
- 원인: 시간 관련 쿼리 파싱 또는 정렬 로직 개선 필요

### 3. 비율/백분율 (percentage) 문제 - 2개 실패
- "What percentage..." 형태의 질문에서 백분율 계산 실패
- 예: "74.9%", "76.1%" 등의 값이 응답에 없음

### 4. 상태 확인 (status) 문제 - 4개 실패
- 특정 CI의 상태(active, monitoring) 조회 실패
- 예: "What is the status of ERP System?" → "active" 미포함

---

## 🔍 응답 품질 관찰 사항

### 긍정적 측면
1. **이력 조회**는 100% 성공 - 작업/유지보수 이력 질의에 강함
2. **유형/순위 질의**에서 좋은 성과 - threshold_alarm, SW 등 정확히 반환
3. **요약 질의**에서 부분적 성공 - 전체 시스템 요약에서 280 포함

### 개선 필요 사항
1. **숫자 포맷팅** - 31,243 vs 31243 형태 불일치 (Test 58은 formatted로 성공)
2. **Neo4j 연결 오류** - 일부 응답에서 "Neo4j source asset not found" 경고
3. **한국어 응답** - 한국어로 응답하여 영어 expected value와 불일치 가능성

---

## 📁 상세 결과 파일

- **JSON 결과**: `artifacts/ops_test_extended_results.json`
- **테스트 케이스**: `docs/OPS_TEST_CASE_EXTENDED.md`
- **테스트 스크립트**: `scripts/test_ops_extended.py`

---

## 💡 개선 제안

1. **숫자 검증 로직 개선**
   - 쉼표 포함/미포함 모두 검사 (현재 적용됨)
   - 한국어 숫자 표현 (만, 천 등) 추가 검증

2. **최근/시간 관련 쿼리 개선**
   - "most recent" → 정렬 후 첫 번째 항목 반환 로직 확인
   - 날짜 형식 통일 (YYYY-MM-DD)

3. **상태 조회 개선**
   - CI 상태 필드 매핑 확인
   - "active", "monitoring" 등 상태 값 검증 강화

4. **백분율 계산**
   - 비율 관련 쿼리에 대한 별도 처리 로직 추가

---

**생성일**: 2026-02-17 20:37