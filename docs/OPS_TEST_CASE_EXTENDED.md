# 📋 OPS 확장 테스트 케이스 (60개)

**생성일**: 2026-02-17
**기준**: 실제 Database에 존재하는 데이터를 기반으로 한 다양한 유형의 질의

---

## 📊 질문 유형 분류

| 유형 | 설명 | 테스트 번호 |
|------|------|------------|
| 개수 세기 | How many... | 1-10 |
| 값 확인 | What is the... / What are... | 11-20 |
| 분포/비율 | Distribution, Percentage | 21-25 |
| 최근/이전 | Most recent, Last, Before | 26-32 |
| 상태 확인 | Status, Condition | 33-38 |
| 이력 조회 | History of, What happened | 39-44 |
| 특정 대상 | For ERP System, For specific CI | 45-50 |
| 비교/순위 | Top, Most, Best | 51-55 |
| 복합 질의 | Multiple conditions | 56-60 |

---

## A. 개수 세기 (1-10)

### Test 1: 전체 CI 개수
**질의**: What is the total number of CIs in the system?
**예상 답변**: 280

### Test 2: 활성 CI 개수
**질의**: How many CIs are currently active?
**예상 답변**: 259

### Test 3: 모니터링 CI 개수
**질의**: How many CIs are in monitoring status?
**예상 답변**: 21

### Test 4: 소프트웨어 CI 개수
**질의**: How many software CIs are there?
**예상 답변**: 197

### Test 5: 하드웨어 CI 개수
**질의**: How many hardware CIs are there?
**예상 답변**: 75

### Test 6: 전체 이벤트 개수
**질의**: How many events are recorded in total?
**예상 답변**: 31,243

### Test 7: 전체 문서 개수
**질의**: How many documents are stored in the system?
**예상 답변**: 132

### Test 8: 작업 이력 개수
**질의**: How many work history entries exist?
**예상 답변**: 1,731

### Test 9: 유지보수 이력 개수
**질의**: How many maintenance activities have been performed?
**예상 답변**: 1,478

### Test 10: 감사 로그 개수
**질의**: How many audit log entries are there?
**예상 답변**: 733

---

## B. 값 확인 (11-20)

### Test 11: 가장 큰 문서 크기
**질의**: What is the size of the largest document?
**예상 답변**: 8,080,776 bytes (레드햇리눅스7_관리자매뉴얼.pdf)

### Test 12: 가장 큰 문서 이름
**질의**: What is the name of the largest document in the system?
**예상 답변**: 레드햇리눅스7_관리자매뉴얼.pdf

### Test 13: PDF 문서 수
**질의**: How many PDF documents are there?
**예상 답변**: 78

### Test 14: 텍스트 문서 수
**질의**: How many plain text documents are there?
**예상 답변**: 54

### Test 15: 가장 많은 이벤트 유형
**질의**: What is the most common event type?
**예상 답변**: threshold_alarm (6,291개)

### Test 16: 가장 많은 CI 유형
**질의**: What is the most common CI type?
**예상 답변**: SW (197개)

### Test 17: 전체 메트릭 개수
**질의**: How many metrics are defined?
**예상 답변**: 120

### Test 18: 메트릭 데이터 포인트 수
**질의**: How many metric data points are recorded?
**예상 답변**: 10,800,000

### Test 19: 문서 카테고리 종류
**질의**: What document categories exist?
**예상 답변**: manual, other

### Test 20: 가장 많은 작업 유형
**질의**: What is the most common work type?
**예상 답변**: audit (455개)

---

## C. 분포/비율 (21-25)

### Test 21: CI 유형별 분포
**질의**: Show me the distribution of CI types.
**예상 답변**: SW: 197, HW: 75, SYSTEM: 8

### Test 22: 이벤트 유형별 분포
**질의**: What is the distribution of event types?
**예상 답변**: threshold_alarm: 6,291, security_alert: 6,286, health_check: 6,267, status_change: 6,225, deployment: 6,174

### Test 23: CI 상태별 분포
**질의**: Show the distribution of CI statuses.
**예상 답변**: active: 259, monitoring: 21

### Test 24: 작업 결과 비율
**질의**: What percentage of work items succeeded?
**예상 답변**: 74.9% (1,297 success / 1,731 total)

### Test 25: 유지보수 결과 비율
**질의**: What is the success rate of maintenance activities?
**예상 답변**: 76.1% (1,125 success / 1,478 total)

---

## D. 최근/이전 (26-32)

### Test 26: 가장 최근 이벤트
**질의**: What was the most recent event?
**예상 답변**: status_change event on 2026-01-01 08:59:17

### Test 27: 가장 최근 이벤트 유형
**질의**: What type of event occurred most recently?
**예상 답변**: status_change

### Test 28: 최근 24시간 이벤트
**질의**: How many events occurred in the last 24 hours?
**예상 답변**: 0

### Test 29: 오늘 발생한 이벤트
**질의**: How many events occurred today?
**예상 답변**: 0

### Test 30: 오늘 기록된 메트릭 값
**질의**: How many metric values were recorded today?
**예상 답변**: 0

### Test 31: 두 번째로 최근 이벤트 유형
**질의**: What was the second most recent event type?
**예상 답변**: deployment

### Test 32: 이벤트 발생 시점
**질의**: When did the most recent security alert occur?
**예상 답변**: 2026-01-01 08:55:50

---

## E. 상태 확인 (33-38)

### Test 33: ERP System 상태
**질의**: What is the status of ERP System?
**예상 답변**: active

### Test 34: ERP Server 01 상태
**질의**: What is the current status of ERP Server 01?
**예상 답변**: monitoring

### Test 35: 모니터링 상태 CI 목록
**질의**: Which CIs are in monitoring status?
**예상 답변**: ERP Server 01, ERP Server 02, ... (21개)

### Test 36: 비활성 CI 존재 여부
**질의**: Are there any inactive CIs?
**예상 답변**: No, all CIs are either active (259) or monitoring (21)

### Test 37: 문서 처리 상태
**질의**: How many documents are successfully processed?
**예상 답변**: (status='done'인 문서 수)

### Test 38: 처리 실패 문서
**질의**: Are there any documents that failed to process?
**예상 답변**: (status='error'인 문서 수 확인)

---

## F. 이력 조회 (39-44)

### Test 39: 작업 이력 요약
**질의**: What types of work have been performed?
**예상 답변**: audit (455), integration (433), upgrade (423), deployment (420)

### Test 40: 유지보수 이력 유형
**질의**: What types of maintenance have been performed?
**예상 답변**: capacity (384), patch (378), inspection (369), reboot (347)

### Test 41: 배포 작업 횟수
**질의**: How many deployment work items have been executed?
**예상 답변**: 420

### Test 42: 성공한 작업 수
**질의**: How many work items completed successfully?
**예상 답변**: 1,297

### Test 43: degraded 결과 작업
**질의**: How many work items resulted in degraded status?
**예상 답변**: 434

### Test 44: 리부트 유지보수 수
**질의**: How many reboot maintenance activities have been done?
**예상 답변**: 347

---

## G. 특정 대상 (45-50)

### Test 45: ERP System 정보
**질의**: Tell me about ERP System.
**예상 답변**: CI Type: SYSTEM, Status: active

### Test 46: ERP Server 01 상세
**질의**: What can you tell me about ERP Server 01?
**예상 답변**: CI Type: HW, Status: monitoring

### Test 47: ERP 관련 CI 목록
**질의**: List all CIs related to ERP.
**예상 답변**: ERP System, ERP Server 01, ERP OS 01, ERP WAS 01, ... 

### Test 48: Linux 관련 문서
**질의**: Find documents about Linux.
**예상 답변**: 레드햇리눅스7_관리자매뉴얼.pdf

### Test 49: 심각도 5 이벤트
**질의**: How many events have severity level 5?
**예상 답변**: 3,134

### Test 50: 심각도 1 이벤트
**질의**: How many events have severity level 1?
**예상 답변**: 6,310

---

## H. 비교/순위 (51-55)

### Test 51: 가장 많은 이벤트 유형
**질의**: Which event type occurs most frequently?
**예상 답변**: threshold_alarm with 6,291 occurrences

### Test 52: Top 3 이벤트 유형
**질의**: What are the top 3 most common event types?
**예상 답변**: threshold_alarm (6,291), security_alert (6,286), health_check (6,267)

### Test 53: 가장 성공적인 유지보수 유형
**질의**: Which maintenance type has the highest success rate?
**예상 답변**: (유지보수 유형별 성공률 계산 필요)

### Test 54: 가장 많은 작업 유형
**질의**: Which work type is most common?
**예상 답변**: audit with 455 items

### Test 55: 심각도별 이벤트 순위
**질의**: Rank event counts by severity level.
**예상 답변**: severity 2 (12,427) > severity 1 (6,310) > severity 3 (6,263) > severity 5 (3,134) > severity 4 (3,109)

---

## I. 복합 질의 (56-60)

### Test 56: 시스템 전체 요약
**질의**: Give me a summary of the overall system status.
**예상 답변**: CI: 280 (259 active, 21 monitoring), Events: 31,243, Documents: 132, Work History: 1,731, Maintenance: 1,478

### Test 57: ERP System 종합 정보
**질의**: Tell me everything about ERP System including its type and status.
**예상 답변**: Name: ERP System, Type: SYSTEM, Status: active

### Test 58: 이벤트 상태 요약
**질의**: Summarize the event status by type and severity.
**예상 답변**: Total 31,243 events across 5 types, severity distribution: 2(12,427), 1(6,310), 3(6,263), 5(3,134), 4(3,109)

### Test 59: 작업 및 유지보수 요약
**질의**: Summarize work and maintenance activities.
**예상 답변**: Work: 1,731 items (74.9% success), Maintenance: 1,478 items (76.1% success)

### Test 60: 문서 시스템 요약
**질의**: Give me a summary of the document management status.
**예상 답변**: 132 documents (78 PDF, 54 text), categories: manual, other

---

## 📋 DB 데이터 기준 (2026-02-17 확인)

| 항목 | 값 | 비고 |
|------|-----|------|
| 전체 CI | 280 | |
| 활성 CI | 259 | |
| 모니터링 CI | 21 | |
| SW CI | 197 | |
| HW CI | 75 | |
| SYSTEM CI | 8 | |
| 전체 이벤트 | 31,243 | |
| threshold_alarm | 6,291 | |
| security_alert | 6,286 | |
| health_check | 6,267 | |
| status_change | 6,225 | |
| deployment | 6,174 | |
| 심각도 1 | 6,310 | |
| 심각도 2 | 12,427 | |
| 심각도 3 | 6,263 | |
| 심각도 4 | 3,109 | |
| 심각도 5 | 3,134 | |
| 문서 | 132 | |
| PDF 문서 | 78 | |
| 텍스트 문서 | 54 | |
| 작업 이력 | 1,731 | |
| audit 작업 | 455 | |
| integration 작업 | 433 | |
| upgrade 작업 | 423 | |
| deployment 작업 | 420 | |
| 성공 작업 | 1,297 | |
| degraded 작업 | 434 | |
| 유지보수 이력 | 1,478 | |
| capacity 유지보수 | 384 | |
| patch 유지보수 | 378 | |
| inspection 유지보수 | 369 | |
| reboot 유지보수 | 347 | |
| 성공 유지보수 | 1,125 | |
| degraded 유지보수 | 353 | |
| 메트릭 | 120 | |
| 메트릭 값 | 10,800,000 | |
| 감사 로그 | 733 | |
| 최근 이벤트 | 2026-01-01 08:59:17 | status_change |