#!/usr/bin/env python3
"""DB 실제 데이터 검증 스크립트 v2 - 트랜잭션 롤백 처리"""
import psycopg

conn_str = "host=115.21.12.151 port=5432 dbname=spadb user=spa password=WeMB1! connect_timeout=10"

def run_query(conn_str, query):
    try:
        with psycopg.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return rows
    except Exception as e:
        return f"ERROR: {e}"

# 먼저 테이블 목록 확인
print("=== 테이블 목록 ===")
result = run_query(conn_str, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
if isinstance(result, list):
    for row in result:
        print(f"  {row[0]}")
else:
    print(result)

print("\n=== CI 관련 ===")
queries = [
    ('CI_total', 'SELECT COUNT(*) FROM ci'),
    ('CI_active', "SELECT COUNT(*) FROM ci WHERE status='active'"),
    ('CI_monitoring', "SELECT COUNT(*) FROM ci WHERE status='monitoring'"),
    ('CI_SW', "SELECT COUNT(*) FROM ci WHERE ci_type='SW'"),
    ('CI_HW', "SELECT COUNT(*) FROM ci WHERE ci_type='HW'"),
    ('CI_SYSTEM', "SELECT COUNT(*) FROM ci WHERE ci_type='SYSTEM'"),
    ('ERP_System_status', "SELECT name, status, ci_type FROM ci WHERE name='ERP System' LIMIT 1"),
    ('ERP_Server01_status', "SELECT name, status, ci_type FROM ci WHERE name='ERP Server 01' LIMIT 1"),
]
for name, q in queries:
    r = run_query(conn_str, q)
    print(f"  {name}: {r[0] if isinstance(r, list) and r else r}")

print("\n=== 이벤트 관련 ===")
queries = [
    ('event_total', 'SELECT COUNT(*) FROM event_log'),
    ('event_threshold_alarm', "SELECT COUNT(*) FROM event_log WHERE event_type='threshold_alarm'"),
    ('event_security_alert', "SELECT COUNT(*) FROM event_log WHERE event_type='security_alert'"),
    ('event_health_check', "SELECT COUNT(*) FROM event_log WHERE event_type='health_check'"),
    ('event_status_change', "SELECT COUNT(*) FROM event_log WHERE event_type='status_change'"),
    ('event_deployment', "SELECT COUNT(*) FROM event_log WHERE event_type='deployment'"),
    ('severity_1', 'SELECT COUNT(*) FROM event_log WHERE severity=1'),
    ('severity_2', 'SELECT COUNT(*) FROM event_log WHERE severity=2'),
    ('severity_3', 'SELECT COUNT(*) FROM event_log WHERE severity=3'),
    ('severity_4', 'SELECT COUNT(*) FROM event_log WHERE severity=4'),
    ('severity_5', 'SELECT COUNT(*) FROM event_log WHERE severity=5'),
    ('recent_event', 'SELECT event_type, time FROM event_log ORDER BY time DESC LIMIT 1'),
    ('second_recent', 'SELECT event_type, time FROM event_log ORDER BY time DESC LIMIT 1 OFFSET 1'),
    ('recent_security_alert', "SELECT time FROM event_log WHERE event_type='security_alert' ORDER BY time DESC LIMIT 1"),
]
for name, q in queries:
    r = run_query(conn_str, q)
    print(f"  {name}: {r[0] if isinstance(r, list) and r else r}")

print("\n=== 문서 관련 (테이블명 탐색) ===")
# 문서 관련 테이블 찾기
doc_tables = ['document', 'tb_document', 'documents', 'doc', 'ops_document', 'ci_document']
for tbl in doc_tables:
    r = run_query(conn_str, f"SELECT COUNT(*) FROM {tbl}")
    if isinstance(r, list):
        print(f"  {tbl}: {r[0][0]}")
    else:
        print(f"  {tbl}: NOT FOUND")

print("\n=== 작업/유지보수 이력 (테이블명 탐색) ===")
work_tables = ['work_history', 'tb_work_history', 'work_log', 'ci_work_history']
for tbl in work_tables:
    r = run_query(conn_str, f"SELECT COUNT(*) FROM {tbl}")
    if isinstance(r, list):
        print(f"  {tbl}: {r[0][0]}")
    else:
        print(f"  {tbl}: NOT FOUND")

maint_tables = ['maintenance_history', 'tb_maintenance_history', 'maintenance_log', 'ci_maintenance_history']
for tbl in maint_tables:
    r = run_query(conn_str, f"SELECT COUNT(*) FROM {tbl}")
    if isinstance(r, list):
        print(f"  {tbl}: {r[0][0]}")
    else:
        print(f"  {tbl}: NOT FOUND")

print("\n=== 기타 테이블 탐색 ===")
other_tables = ['tb_audit_log', 'audit_log', 'metrics', 'metric_value', 'tb_metrics', 'tb_metric_value']
for tbl in other_tables:
    r = run_query(conn_str, f"SELECT COUNT(*) FROM {tbl}")
    if isinstance(r, list):
        print(f"  {tbl}: {r[0][0]}")
    else:
        print(f"  {tbl}: NOT FOUND")

print("\nDB 검증 완료")
