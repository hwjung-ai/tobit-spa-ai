# 20개 테스트 질의 및 검증 계획

## 목표
- 구성, 메트릭, 연관, 이력 테이블을 기반으로 의미 있는 20개 질의 생성
- 각 질의의 소요시간 측정
- 응답 정확도 90% 이상 달성
- 부정확한 응답의 경우 trace_id 기반 추적 및 asset 문제 분석
- 문제 해결을 통한 시스템 완성도 향상

---

## 테스트 질의 설정

### 테이블 범위
1. **구성 (Configuration)**: tb_asset_registry, tb_operation_settings, ci, ci_ext
2. **메트릭 (Metrics)**: metric_def, metric_value
3. **연관 (Relationships)**: tb_ci_change, tb_ci_integrity_issue, tb_ci_duplicate
4. **이력 (History)**: maintenance_history, work_history, tb_audit_log

### 질의 카테고리 분포
- **구성 기반**: 5개 (Q1-Q5)
- **메트릭 기반**: 5개 (Q6-Q10)
- **연관 기반**: 5개 (Q11-Q15)
- **이력 기반**: 5개 (Q16-Q20)

---

## 20개 테스트 질의 정의

### 구성 관련 질의 (Configuration)

#### Q1: 발행된 asset 통계
**질의**: "현재 시스템에서 발행된 asset의 유형별 개수는 얼마나 되는가?"

**기대 응답**:
```json
{
  "prompt": 20,
  "policy": 11,
  "mapping": 17,
  "source": 2,
  "schema": 3,
  "resolver": 4,
  "query": 131,
  "screen": 12,
  "tool": 12,
  "catalog": 0,
  "total": 212
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q2: 특정 버전의 최신 asset
**질의**: "prompt asset 중에서 가장 최신 버전으로 발행된 것의 이름과 버전은?"

**기대 응답**:
```json
{
  "name": "ci_planner_output_parser",
  "version": 1,
  "asset_type": "prompt",
  "status": "published",
  "created_by": "system"
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q3: Asset의 의존성 체인
**질의**: "view_depth_policies를 사용하는 모든 query asset은 몇 개인가?"

**기대 응답**:
```json
{
  "policy_name": "view_depth_policies",
  "dependent_queries": [
    "query_id_1",
    "query_id_2",
    "query_id_3"
  ],
  "count": 3
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q4: Operation Settings의 활성 설정
**질의**: "현재 operation_settings에서 활성화된 설정의 개수는?"

**기대 응답**:
```json
{
  "total_settings": 8,
  "published_settings": 7,
  "draft_settings": 1,
  "settings_requiring_restart": 2
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q5: CI 구성 현황
**질의**: "전체 CI 자산 중에서 HW 타입의 개수와 현재 상태 분포는?"

**기대 응답**:
```json
{
  "ci_type": "HW",
  "total_count": 15,
  "status_distribution": {
    "active": 12,
    "inactive": 2,
    "maintenance": 1
  }
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

### 메트릭 관련 질의 (Metrics)

#### Q6: 최근 24시간 성능 메트릭
**질의**: "지난 24시간 동안 record_count 메트릭의 평균값과 최대값은?"

**기대 응답**:
```json
{
  "metric_name": "record_count",
  "time_period": "last_24h",
  "average_value": 45230.5,
  "max_value": 52100,
  "min_value": 38900,
  "sample_count": 1440
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q7: 메트릭 품질 평가
**질의**: "gauge 타입 메트릭 중에서 'good' 품질 데이터의 비율은?"

**기대 응답**:
```json
{
  "metric_type": "gauge",
  "total_readings": 5280,
  "good_quality": 5100,
  "quality_percentage": 96.6,
  "date_range": "2024-01-01 ~ 2024-01-29"
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q8: 특정 CI의 메트릭 추이
**질의**: "ci_id 'system_001'의 지난 7일 동안의 cpu_usage 메트릭 추이는?"

**기대 응답**:
```json
{
  "ci_id": "system_001",
  "metric_name": "cpu_usage",
  "period": "7_days",
  "readings": [
    {"timestamp": "2024-01-29T00:00:00Z", "value": 45.2, "quality": "good"},
    {"timestamp": "2024-01-29T06:00:00Z", "value": 52.1, "quality": "good"}
  ],
  "trend": "increasing"
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q9: 메트릭 임계값 위반
**질의**: "memory_usage 메트릭이 80% 이상인 CI가 지난 1시간에 몇 개나 있었는가?"

**기대 응답**:
```json
{
  "metric_name": "memory_usage",
  "threshold": 80,
  "time_window": "1_hour",
  "affected_ci_count": 3,
  "affected_cis": ["system_001", "system_002", "system_003"],
  "max_violation": 94.2
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q10: 메트릭 데이터 완전성
**질의**: "지난 1개월 동안 메트릭 데이터의 수집 완전성은 95% 이상인가?"

**기대 응답**:
```json
{
  "period": "1_month",
  "expected_readings": 43200,
  "actual_readings": 42576,
  "completeness_percentage": 98.6,
  "status": "healthy"
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

### 연관 관련 질의 (Relationships)

#### Q11: CI 변경 이력
**질의**: "지난 30일 동안 'system_001' CI의 update 타입 변경은 몇 건인가?"

**기대 응답**:
```json
{
  "ci_id": "system_001",
  "period": "30_days",
  "change_type": "update",
  "total_changes": 5,
  "approved": 5,
  "rejected": 0,
  "pending": 0,
  "changed_by": ["user_001", "user_002"],
  "recent_changes": [
    {
      "id": "change_001",
      "timestamp": "2024-01-28T14:00:00Z",
      "old_values": {"status": "active"},
      "new_values": {"status": "maintenance"},
      "approved_by": "user_admin"
    }
  ]
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q12: CI 무결성 문제
**질의**: "현재 미해결 상태의 CI 무결성 문제는 총 몇 개인가?"

**기대 응답**:
```json
{
  "unresolved_issues": 7,
  "by_severity": {
    "critical": 2,
    "high": 3,
    "medium": 2,
    "low": 0
  },
  "by_issue_type": {
    "duplicate": 3,
    "missing_dependency": 2,
    "invalid_config": 2
  }
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q13: CI 중복 감지
**질의**: "유사도가 95% 이상인 CI 중복 쌍은 몇 개인가?"

**기대 응답**:
```json
{
  "similarity_threshold": 0.95,
  "duplicate_pairs": 3,
  "merged": 1,
  "unmerged": 2,
  "pairs": [
    {
      "ci_id_1": "sys_001",
      "ci_id_2": "sys_001_backup",
      "similarity_score": 0.98,
      "is_merged": false
    }
  ]
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q14: CI 관계 복잡도
**질의**: "가장 많은 관계를 가진 CI는 어떤 것이고, 관계 개수는?"

**기대 응답**:
```json
{
  "most_connected_ci": "system_core",
  "relationship_count": 23,
  "relationship_types": {
    "depends_on": 8,
    "supports": 10,
    "conflicts_with": 1,
    "duplicate_of": 4
  },
  "critical_dependencies": 5
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q15: CI 변경 승인 프로세스
**질의**: "지난 7일 동안 대기 중인 CI 변경 신청은 몇 건이고, 평균 대기 시간은?"

**기대 응답**:
```json
{
  "period": "7_days",
  "pending_changes": 2,
  "approved_changes": 8,
  "rejected_changes": 1,
  "average_approval_time_hours": 4.2,
  "slowest_approval_hours": 12.5,
  "pending_details": [
    {
      "change_id": "change_pending_001",
      "ci_id": "system_002",
      "requested_by": "user_003",
      "hours_waiting": 6.5
    }
  ]
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

### 이력 관련 질의 (History)

#### Q16: 유지보수 이력 통계
**질의**: "지난 3개월 동안 성공적으로 완료된 유지보수 작업은 몇 건이고, 평균 소요 시간은?"

**기대 응답**:
```json
{
  "period": "3_months",
  "total_maintenance": 24,
  "successful": 23,
  "failed": 1,
  "average_duration_minutes": 45.3,
  "by_type": {
    "preventive": 12,
    "corrective": 10,
    "adaptive": 1,
    "perfective": 1
  },
  "by_performer": {
    "team_ops": 15,
    "team_support": 8
  }
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q17: 업무 이력 분석
**질의**: "현재 월의 업무 신청 중에서 승인 완료율이 가장 높은 부서는?"

**기대 응답**:
```json
{
  "current_month": "2024-01",
  "department_approval_rates": [
    {
      "department": "platform_team",
      "total_requests": 15,
      "approved": 14,
      "rejected": 1,
      "approval_rate": 93.3
    },
    {
      "department": "infra_team",
      "total_requests": 8,
      "approved": 8,
      "rejected": 0,
      "approval_rate": 100.0
    }
  ],
  "highest_approver": "infra_team"
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q18: 감사 로그 추적
**질의**: "특정 trace_id의 모든 변경 사항을 기록한 감사 로그는 몇 개인가?"

**기대 응답**:
```json
{
  "trace_id": "7a3e39d9-1b32-4e93-be11-cc3ad4a820e1",
  "total_audit_records": 12,
  "by_action": {
    "create": 1,
    "update": 8,
    "delete": 1,
    "export": 2
  },
  "by_actor": {
    "system": 8,
    "user_001": 4
  },
  "time_span_seconds": 3600
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q19: 문제 해결 시간 추이
**질의**: "지난 1개월 동안 'critical' 심각도의 CI 무결성 문제들의 평균 해결 시간은?"

**기대 응답**:
```json
{
  "period": "1_month",
  "severity": "critical",
  "total_issues": 5,
  "resolved": 4,
  "unresolved": 1,
  "average_resolution_hours": 8.25,
  "resolution_times": [6.5, 8, 9, 10],
  "fastest_resolution_hours": 6.5,
  "slowest_resolution_hours": 10
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

#### Q20: 시스템 활동 현황
**질의**: "지난 24시간 동안의 시스템 감사 활동(생성, 수정, 삭제)의 시간대별 분포는?"

**기대 응답**:
```json
{
  "period": "24_hours",
  "total_events": 156,
  "by_hour": [
    {"hour": 0, "count": 4},
    {"hour": 1, "count": 2},
    {"hour": 6, "count": 12},
    {"hour": 12, "count": 28},
    {"hour": 18, "count": 18}
  ],
  "peak_hour": 12,
  "peak_count": 28,
  "by_action": {
    "create": 32,
    "update": 98,
    "delete": 8,
    "other": 18
  }
}
```

**소요시간**: _____ ms
**실제 응답**: _____
**정확도**: _____ %
**Trace ID**: _____

---

## 실행 계획

### Phase 1: 자동화된 질의 실행 (자동 생성)
- Python 스크립트로 API/DB를 통해 질의 자동 실행
- 각 질의별 소요시간 측정
- 응답 결과 저장

### Phase 2: 정확도 검증 (수동/자동 혼합)
- 예상 응답과 실제 응답 비교
- 정확도 계산 (매칭율 기반)
- 불일치 항목 분류

### Phase 3: 문제 분석 (Trace 기반)
- 부정확한 응답에 대해 trace_id 추적
- 각 stage별 적용된 asset 확인
- 문제의 원인 파악 (asset 문제 vs 코드 문제)

### Phase 4: 개선 및 반복
- 식별된 문제 해결
- 코드/asset 수정
- 90% 이상 정확도 달성까지 반복

---

## 검증 기준

### 정확도 평가 방식
```
정확도 = (일치하는 필드 수 / 전체 필드 수) × 100%
```

### 통과 기준
- 전체 질의의 90% 이상이 90% 이상의 정확도 달성
- 즉, 20개 중 최소 18개가 90% 이상 정확도

### 추적 및 개선
- 90% 미만인 질의에 대해 trace 분석
- Asset 또는 소스 데이터 문제 파악
- 반복 개선

---

## 예상 출력 파일
1. **20_TEST_QUERIES_RESULTS.md** - 각 질의의 실행 결과 및 정확도
2. **ACCURACY_SUMMARY.md** - 전체 정확도 요약 및 문제점 분석
3. **PROBLEM_TRACE_ANALYSIS.md** - 불정확한 질의의 추적 분석
4. **SYSTEM_IMPROVEMENTS.md** - 식별된 문제와 개선사항

