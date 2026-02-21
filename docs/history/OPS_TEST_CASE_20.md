# 📋 20개 테스트 케이스 (실제 DB 데이터 기반)

**생성일**: 2026-01-29
**기준**: 실제 Database에 존재하는 데이터를 쿼리한 정확한 질의와 답변

---

## Test 1: What is the current system status? Tell me the total number of CIs.

**질의**: What is the current system status? Tell me the total number of CIs.

**SQL 근거**:
```sql
SELECT COUNT(*) as total_ci FROM ci
```

**조회 결과**: 280

**정답**: There are 280 CIs in the system.

---

## Test 2: What is the most common CI type in the system?

**질의**: What is the most common CI type in the system?

**SQL 근거**:
```sql
SELECT ci_type, COUNT(*) FROM ci GROUP BY ci_type ORDER BY COUNT(*) DESC
```

**조회 결과**: 197

**정답**: The most common CI type is SW with 197 instances.

---

## Test 3: How many events are recorded in the system?

**질의**: How many events are recorded in the system?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log
```

**조회 결과**: 31,243

**정답**: There are 31,243 events recorded in the system.

---

## Test 4: What is the most common event type?

**질의**: What is the most common event type?

**SQL 근거**:
```sql
SELECT event_type, COUNT(*) FROM event_log GROUP BY event_type ORDER BY COUNT(*) DESC
```

**조회 결과**: 6,291

**정답**: The most common event type is threshold_alarm with 6,291 occurrences.

---

## Test 5: How many events occurred in the last 24 hours?

**질의**: How many events occurred in the last 24 hours?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE time > NOW() - INTERVAL '24 hours'
```

**조회 결과**: 0

**정답**: 0 events occurred in the last 24 hours.

---

## Test 6: How many metrics are defined in the system?

**질의**: How many metrics are defined in the system?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM metrics
```

**조회 결과**: 120

**정답**: There are 120 metrics defined in the system.

---

## Test 7: How many metric data points are recorded?

**질의**: How many metric data points are recorded?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM metric_value
```

**조회 결과**: 10,800,000

**정답**: There are 10,800,000 metric data points recorded.

---

## Test 8: How many CIs are currently in active status?

**질의**: How many CIs are currently in active status?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM ci WHERE status = 'active'
```

**조회 결과**: 259

**정답**: 259 CIs are in active status.

---

## Test 9: How many software and hardware CIs do we have?

**질의**: How many software and hardware CIs do we have?

**SQL 근거**:
```sql
SELECT ci_type, COUNT(*) FROM ci WHERE ci_type IN ('SW', 'HW') GROUP BY ci_type
```

**조회 결과**: 272

**정답**: We have 197 Software CIs and 75 Hardware CIs.

---

## Test 10: How many audit log entries are there?

**질의**: How many audit log entries are there?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM tb_audit_log
```

**조회 결과**: 733

**정답**: There are 733 audit log entries.

---

## Test 11: How many system-type CIs exist?

**질의**: How many system-type CIs exist?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM ci WHERE ci_type = 'SYSTEM'
```

**조회 결과**: 8

**정답**: There are 8 system-type CIs.

---

## Test 12: How many events occurred today?

**질의**: How many events occurred today?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE DATE(time) = CURRENT_DATE
```

**조회 결과**: 0

**정답**: 0 events occurred today.

---

## Test 13: How many metric values were recorded today?

**질의**: How many metric values were recorded today?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM metric_value WHERE DATE(time) = CURRENT_DATE
```

**조회 결과**: 0

**정답**: 0 metric values were recorded today.

---

## Test 14: What was the most recent event type?

**질의**: What was the most recent event type?

**SQL 근거**:
```sql
SELECT event_type FROM event_log ORDER BY time DESC LIMIT 1
```

**조회 결과**: 1

**정답**: The most recent event type was status_change.

---

## Test 15: How many threshold alarms have occurred?

**질의**: How many threshold alarms have occurred?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE event_type = 'threshold_alarm'
```

**조회 결과**: 6,291

**정답**: 6,291 threshold alarms have occurred.

---

## Test 16: How many security alerts have been raised?

**질의**: How many security alerts have been raised?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE event_type = 'security_alert'
```

**조회 결과**: 6,286

**정답**: 6,286 security alerts have been raised.

---

## Test 17: How many health check events are there?

**질의**: How many health check events are there?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE event_type = 'health_check'
```

**조회 결과**: 6,267

**정답**: 6,267 health check events have been recorded.

---

## Test 18: How many status change events have occurred?

**질의**: How many status change events have occurred?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE event_type = 'status_change'
```

**조회 결과**: 6,225

**정답**: 6,225 status change events have occurred.

---

## Test 19: How many deployment events have been recorded?

**질의**: How many deployment events have been recorded?

**SQL 근거**:
```sql
SELECT COUNT(*) FROM event_log WHERE event_type = 'deployment'
```

**조회 결과**: 6,174

**정답**: 6,174 deployment events have been recorded.

---

## Test 20: How many distinct CI names are there in the system?

**질의**: How many distinct CI names are there in the system?

**SQL 근거**:
```sql
SELECT COUNT(DISTINCT ci_name) FROM ci
```

**조회 결과**: 280

**정답**: There are 280 distinct CI names in the system.

---

