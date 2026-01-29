# 🔧 Query Asset 수정 계획

**문제**: Query Asset의 schema_json이 NULL이므로 실제 쿼리가 실행되지 않음

## 20개 테스트에 필요한 Query Asset

### 1. System Status 관련 (테스트 #1-3)

#### Asset: "system_status_query"
```json
{
  "name": "system_status_query",
  "description": "시스템 상태 조회",
  "keywords": ["status", "system", "current"],
  "sql": "SELECT COUNT(*) as cnt FROM ci WHERE status = 'active'",
  "source": "primary_postgres",
  "output_type": "metric"
}
```

#### Asset: "ci_information_query"
```json
{
  "name": "ci_information_query",
  "description": "시스템 정보 조회",
  "keywords": ["information", "system", "info"],
  "sql": "SELECT ci_id, ci_name, ci_type, status FROM ci LIMIT 10",
  "source": "primary_postgres",
  "output_type": "list"
}
```

#### Asset: "running_services_query"
```json
{
  "name": "running_services_query",
  "description": "실행 중인 서비스 조회",
  "keywords": ["services", "running", "active"],
  "sql": "SELECT COUNT(*) as service_count FROM ci WHERE ci_type = 'service' AND status = 'active'",
  "source": "primary_postgres",
  "output_type": "metric"
}
```

### 2. Metrics 관련 (테스트 #4-8)

#### Asset: "performance_metrics_query"
```json
{
  "name": "performance_metrics_query",
  "description": "성능 메트릭 조회",
  "keywords": ["metrics", "performance", "key"],
  "sql": "SELECT metric_id, metric_name, recent_value FROM metrics WHERE metric_type = 'performance' LIMIT 10",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "last_24h_metrics_query"
```json
{
  "name": "last_24h_metrics_query",
  "description": "최근 24시간 메트릭",
  "keywords": ["metrics", "24", "hours", "last"],
  "sql": "SELECT metric_id, metric_name, AVG(metric_value) as avg_value FROM metric_value WHERE recorded_time > NOW() - INTERVAL '24 hours' GROUP BY metric_id, metric_name",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "resource_usage_query"
```json
{
  "name": "resource_usage_query",
  "description": "리소스 사용량 조회",
  "keywords": ["resource", "usage", "cpu", "memory"],
  "sql": "SELECT metric_id, metric_name, recent_value FROM metrics WHERE metric_name IN ('cpu_usage', 'memory_usage', 'disk_usage')",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "daily_records_query"
```json
{
  "name": "daily_records_query",
  "description": "오늘 처리된 레코드 수",
  "keywords": ["records", "processed", "today", "count"],
  "sql": "SELECT COUNT(*) as record_count FROM event_log WHERE DATE(created_at) = CURRENT_DATE",
  "source": "primary_postgres",
  "output_type": "metric"
}
```

#### Asset: "avg_response_time_query"
```json
{
  "name": "avg_response_time_query",
  "description": "평균 응답 시간",
  "keywords": ["response", "time", "average"],
  "sql": "SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_response_time_ms FROM event_log WHERE completed_at IS NOT NULL",
  "source": "primary_postgres",
  "output_type": "metric"
}
```

### 3. Relationships 관련 (테스트 #9-12)

#### Asset: "data_dependencies_query"
```json
{
  "name": "data_dependencies_query",
  "description": "데이터 의존성 조회",
  "keywords": ["dependencies", "data", "relations"],
  "sql": "SELECT COUNT(*) as dependency_count FROM ci c1 JOIN ci c2 ON c1.ci_id = c2.parent_ci_id",
  "source": "primary_postgres",
  "output_type": "metric"
}
```

#### Asset: "related_entities_query"
```json
{
  "name": "related_entities_query",
  "description": "관련 엔티티 조회",
  "keywords": ["entities", "related", "users"],
  "sql": "SELECT DISTINCT ci_type, COUNT(*) as count FROM ci GROUP BY ci_type",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "architecture_diagram_query"
```json
{
  "name": "architecture_diagram_query",
  "description": "시스템 아키텍처 조회",
  "keywords": ["architecture", "diagram", "system"],
  "sql": "SELECT ci_id, ci_name, ci_type, parent_ci_id FROM ci WHERE parent_ci_id IS NOT NULL LIMIT 20",
  "source": "primary_postgres",
  "output_type": "graph"
}
```

#### Asset: "dataflow_relations_query"
```json
{
  "name": "dataflow_relations_query",
  "description": "데이터 흐름 관계 조회",
  "keywords": ["dataflow", "relations", "flow"],
  "sql": "SELECT ci_id, ci_name FROM ci WHERE ci_type IN ('database', 'service') LIMIT 15",
  "source": "primary_postgres",
  "output_type": "table"
}
```

### 4. History 관련 (테스트 #13-16)

#### Asset: "recent_changes_query"
```json
{
  "name": "recent_changes_query",
  "description": "최근 변경사항 조회",
  "keywords": ["changes", "recent", "history"],
  "sql": "SELECT event_id, event_type, ci_id, event_time FROM event_log ORDER BY event_time DESC LIMIT 20",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "yesterday_events_query"
```json
{
  "name": "yesterday_events_query",
  "description": "어제 발생한 이벤트",
  "keywords": ["yesterday", "events", "history"],
  "sql": "SELECT COUNT(*) as event_count FROM event_log WHERE DATE(event_time) = CURRENT_DATE - INTERVAL '1 day'",
  "source": "primary_postgres",
  "output_type": "metric"
}
```

#### Asset: "weekly_audit_trail_query"
```json
{
  "name": "weekly_audit_trail_query",
  "description": "지난주 감사 추적",
  "keywords": ["audit", "trail", "week", "last"],
  "sql": "SELECT audit_id, action, created_at FROM tb_audit_log WHERE created_at > NOW() - INTERVAL '7 days' ORDER BY created_at DESC",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "system_state_7days_ago_query"
```json
{
  "name": "system_state_7days_ago_query",
  "description": "7일 전 시스템 상태",
  "keywords": ["state", "system", "7", "days", "ago"],
  "sql": "SELECT * FROM event_log WHERE event_time BETWEEN (NOW() - INTERVAL '8 days') AND (NOW() - INTERVAL '7 days') LIMIT 20",
  "source": "primary_postgres",
  "output_type": "table"
}
```

### 5. Advanced 관련 (테스트 #17-20)

#### Asset: "performance_comparison_query"
```json
{
  "name": "performance_comparison_query",
  "description": "성능 메트릭 비교",
  "keywords": ["performance", "comparison", "metrics", "periods"],
  "sql": "SELECT metric_name, AVG(CASE WHEN recorded_time > NOW() - INTERVAL '1 day' THEN metric_value END) as today_avg, AVG(CASE WHEN recorded_time > NOW() - INTERVAL '8 days' AND recorded_time < NOW() - INTERVAL '7 days' THEN metric_value END) as week_ago_avg FROM metric_value GROUP BY metric_name",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "trends_analysis_query"
```json
{
  "name": "trends_analysis_query",
  "description": "트렌드 분석 및 통계",
  "keywords": ["trends", "analyze", "insights"],
  "sql": "SELECT DATE(event_time) as event_date, COUNT(*) as event_count FROM event_log WHERE event_time > NOW() - INTERVAL '30 days' GROUP BY DATE(event_time) ORDER BY event_date DESC",
  "source": "primary_postgres",
  "output_type": "table"
}
```

#### Asset: "system_report_query"
```json
{
  "name": "system_report_query",
  "description": "포괄적인 시스템 리포트",
  "keywords": ["report", "system", "comprehensive"],
  "sql": "SELECT (SELECT COUNT(*) FROM ci) as total_cis, (SELECT COUNT(*) FROM event_log WHERE DATE(event_time) = CURRENT_DATE) as today_events, (SELECT COUNT(*) FROM metrics) as total_metrics",
  "source": "primary_postgres",
  "output_type": "report"
}
```

#### Asset: "optimization_recommendations_query"
```json
{
  "name": "optimization_recommendations_query",
  "description": "최적화 권장사항",
  "keywords": ["optimization", "recommendations", "system"],
  "sql": "SELECT ci_id, ci_name, COUNT(event_id) as event_count FROM ci LEFT JOIN event_log ON ci.ci_id = event_log.ci_id WHERE event_log.event_type IN ('error', 'warning') GROUP BY ci_id, ci_name HAVING COUNT(event_id) > 5 ORDER BY COUNT(event_id) DESC LIMIT 10",
  "source": "primary_postgres",
  "output_type": "analysis"
}
```

---

## 구현 방법

### Step 1: 기존 Query Asset 삭제
```sql
DELETE FROM tb_asset_registry
WHERE asset_type = 'query' AND schema_json IS NULL;
```

### Step 2: 새 Query Asset 생성
각 Query Asset을 tb_asset_registry에 INSERT

### Step 3: 테스트 재실행
20개 쿼리를 다시 실행하여 실제 답변 확인

---

## 핵심

**schema_json 필드가 NULL이면 Query Asset이 작동하지 않습니다.**
각 Query Asset은 반드시:
1. SQL 쿼리 포함
2. 적절한 keywords
3. output_type 지정
이 있어야 합니다.
