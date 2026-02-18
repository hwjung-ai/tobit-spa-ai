#!/usr/bin/env python3
"""DB 실제 데이터 검증 스크립트"""
import sys
sys.path.insert(0, '/home/spa/tobit-spa-ai/apps/api')

import os
os.environ.setdefault('PG_HOST', '115.21.12.151')
os.environ.setdefault('PG_PORT', '5432')
os.environ.setdefault('PG_DB', 'spadb')
os.environ.setdefault('PG_USER', 'spa')
os.environ.setdefault('PG_PASSWORD', 'WeMB1!')

import psycopg

conn_str = "host=115.21.12.151 port=5432 dbname=spadb user=spa password=WeMB1! connect_timeout=10"

queries = [
    ('CI_total', 'SELECT COUNT(*) FROM ci'),
    ('CI_active', "SELECT COUNT(*) FROM ci WHERE status='active'"),
    ('CI_monitoring', "SELECT COUNT(*) FROM ci WHERE status='monitoring'"),
    ('CI_SW', "SELECT COUNT(*) FROM ci WHERE ci_type='SW'"),
    ('CI_HW', "SELECT COUNT(*) FROM ci WHERE ci_type='HW'"),
    ('CI_SYSTEM', "SELECT COUNT(*) FROM ci WHERE ci_type='SYSTEM'"),
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
    ('doc_total', 'SELECT COUNT(*) FROM document'),
    ('doc_pdf', "SELECT COUNT(*) FROM document WHERE file_type='pdf'"),
    ('doc_text', "SELECT COUNT(*) FROM document WHERE file_type='text'"),
    ('work_total', 'SELECT COUNT(*) FROM work_history'),
    ('work_audit', "SELECT COUNT(*) FROM work_history WHERE work_type='audit'"),
    ('work_integration', "SELECT COUNT(*) FROM work_history WHERE work_type='integration'"),
    ('work_upgrade', "SELECT COUNT(*) FROM work_history WHERE work_type='upgrade'"),
    ('work_deployment', "SELECT COUNT(*) FROM work_history WHERE work_type='deployment'"),
    ('work_success', "SELECT COUNT(*) FROM work_history WHERE result='success'"),
    ('work_degraded', "SELECT COUNT(*) FROM work_history WHERE result='degraded'"),
    ('maint_total', 'SELECT COUNT(*) FROM maintenance_history'),
    ('maint_capacity', "SELECT COUNT(*) FROM maintenance_history WHERE maintenance_type='capacity'"),
    ('maint_patch', "SELECT COUNT(*) FROM maintenance_history WHERE maintenance_type='patch'"),
    ('maint_inspection', "SELECT COUNT(*) FROM maintenance_history WHERE maintenance_type='inspection'"),
    ('maint_reboot', "SELECT COUNT(*) FROM maintenance_history WHERE maintenance_type='reboot'"),
    ('maint_success', "SELECT COUNT(*) FROM maintenance_history WHERE result='success'"),
    ('maint_degraded', "SELECT COUNT(*) FROM maintenance_history WHERE result='degraded'"),
    ('audit_log', 'SELECT COUNT(*) FROM tb_audit_log'),
    ('metrics', 'SELECT COUNT(*) FROM metrics'),
    ('metric_value', 'SELECT COUNT(*) FROM metric_value'),
    ('recent_event_type', 'SELECT event_type FROM event_log ORDER BY time DESC LIMIT 1'),
    ('recent_event_time', 'SELECT time FROM event_log ORDER BY time DESC LIMIT 1'),
    ('second_recent_event', 'SELECT event_type FROM event_log ORDER BY time DESC LIMIT 1 OFFSET 1'),
    ('recent_security_alert', "SELECT time FROM event_log WHERE event_type='security_alert' ORDER BY time DESC LIMIT 1"),
    ('largest_doc_size', 'SELECT MAX(file_size) FROM document'),
    ('largest_doc_name', 'SELECT file_name FROM document ORDER BY file_size DESC LIMIT 1'),
    ('doc_categories', 'SELECT DISTINCT category FROM document ORDER BY category'),
    ('most_common_work_type', 'SELECT work_type, COUNT(*) as cnt FROM work_history GROUP BY work_type ORDER BY cnt DESC LIMIT 1'),
    ('erp_system_status', "SELECT status FROM ci WHERE name='ERP System' LIMIT 1"),
    ('erp_server01_status', "SELECT status, ci_type FROM ci WHERE name='ERP Server 01' LIMIT 1"),
    ('doc_done', "SELECT COUNT(*) FROM document WHERE status='done'"),
    ('doc_error', "SELECT COUNT(*) FROM document WHERE status='error'"),
]

print("DB 데이터 검증 시작...")
with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        for name, q in queries:
            try:
                cur.execute(q)
                rows = cur.fetchall()
                if rows:
                    print(f"{name}: {rows[0][0] if len(rows[0]) == 1 else rows[0]}")
                else:
                    print(f"{name}: (no result)")
            except Exception as e:
                print(f"{name}: ERROR - {e}")

print("\nDB 검증 완료")
