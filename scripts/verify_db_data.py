#!/usr/bin/env python3
"""
OPS_TEST_CASE_20 데이터 검증 스크립트
DB에 접속하여 실제 데이터를 확인합니다.
"""

import os
import sys

# apps/api 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

def main():
    import psycopg
    
    # DB 연결 정보
    pg_host = os.environ.get('PG_HOST', '115.21.12.151')
    pg_port = os.environ.get('PG_PORT', '5432')
    pg_db = os.environ.get('PG_DB', 'spadb')
    pg_user = os.environ.get('PG_USER', 'spa')
    pg_password = os.environ.get('PG_PASSWORD', 'WeMB1!')
    
    conn_str = f'host={pg_host} port={pg_port} dbname={pg_db} user={pg_user} password={pg_password}'
    print(f'Connecting to: {pg_host}:{pg_port}/{pg_db}')
    print('=' * 60)
    
    try:
        with psycopg.connect(conn_str, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                # Test 1: Total CI count
                cur.execute('SELECT COUNT(*) as total_ci FROM ci')
                result = cur.fetchone()
                print(f'Test 1 - Total CI count: {result[0]}')
                
                # Test 2: Most common CI type
                cur.execute('SELECT ci_type, COUNT(*) as cnt FROM ci GROUP BY ci_type ORDER BY cnt DESC LIMIT 1')
                result = cur.fetchone()
                print(f'Test 2 - Most common CI type: {result[0]} with {result[1]} instances')
                
                # Test 3: Total events
                cur.execute('SELECT COUNT(*) FROM event_log')
                result = cur.fetchone()
                print(f'Test 3 - Total events: {result[0]}')
                
                # Test 4: Most common event type
                cur.execute('SELECT event_type, COUNT(*) as cnt FROM event_log GROUP BY event_type ORDER BY cnt DESC LIMIT 1')
                result = cur.fetchone()
                print(f'Test 4 - Most common event type: {result[0]} with {result[1]} occurrences')
                
                # Test 5: Events in last 24 hours
                cur.execute("SELECT COUNT(*) FROM event_log WHERE time > NOW() - INTERVAL '24 hours'")
                result = cur.fetchone()
                print(f'Test 5 - Events in last 24h: {result[0]}')
                
                # Test 6: Total metrics
                cur.execute('SELECT COUNT(*) FROM metrics')
                result = cur.fetchone()
                print(f'Test 6 - Total metrics: {result[0]}')
                
                # Test 7: Metric data points
                cur.execute('SELECT COUNT(*) FROM metric_value')
                result = cur.fetchone()
                print(f'Test 7 - Metric data points: {result[0]}')
                
                # Test 8: Active CIs
                cur.execute("SELECT COUNT(*) FROM ci WHERE status = 'active'")
                result = cur.fetchone()
                print(f'Test 8 - Active CIs: {result[0]}')
                
                # Test 9: SW and HW CIs
                cur.execute("SELECT ci_type, COUNT(*) FROM ci WHERE ci_type IN ('SW', 'HW') GROUP BY ci_type")
                results = cur.fetchall()
                for r in results:
                    print(f'Test 9 - {r[0]} CIs: {r[1]}')
                
                # Test 10: Audit log entries
                cur.execute('SELECT COUNT(*) FROM tb_audit_log')
                result = cur.fetchone()
                print(f'Test 10 - Audit log entries: {result[0]}')
                
                # Test 11: System-type CIs
                cur.execute("SELECT COUNT(*) FROM ci WHERE ci_type = 'SYSTEM'")
                result = cur.fetchone()
                print(f'Test 11 - System-type CIs: {result[0]}')
                
                # Test 12: Events today
                cur.execute('SELECT COUNT(*) FROM event_log WHERE DATE(time) = CURRENT_DATE')
                result = cur.fetchone()
                print(f'Test 12 - Events today: {result[0]}')
                
                # Test 13: Metric values today
                cur.execute('SELECT COUNT(*) FROM metric_value WHERE DATE(time) = CURRENT_DATE')
                result = cur.fetchone()
                print(f'Test 13 - Metric values today: {result[0]}')
                
                # Test 14: Most recent event type
                cur.execute('SELECT event_type FROM event_log ORDER BY time DESC LIMIT 1')
                result = cur.fetchone()
                print(f'Test 14 - Most recent event type: {result[0] if result else None}')
                
                # Test 15-19: Event type counts
                event_types = ['threshold_alarm', 'security_alert', 'health_check', 'status_change', 'deployment']
                for i, et in enumerate(event_types, 15):
                    cur.execute(f"SELECT COUNT(*) FROM event_log WHERE event_type = '{et}'")
                    result = cur.fetchone()
                    print(f'Test {i} - {et} count: {result[0]}')
                
                # Test 20: Distinct CI names
                cur.execute('SELECT COUNT(DISTINCT ci_name) FROM ci')
                result = cur.fetchone()
                print(f'Test 20 - Distinct CI names: {result[0]}')
                
    except Exception as e:
        print(f'Error: {e}')
        raise

if __name__ == '__main__':
    main()