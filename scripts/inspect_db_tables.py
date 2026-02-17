#!/usr/bin/env python3
"""DB 테이블 구조 및 데이터 확인 스크립트"""

import psycopg

conn_str = 'host=115.21.12.151 port=5432 dbname=spadb user=spa password=WeMB1!'

with psycopg.connect(conn_str, connect_timeout=10) as conn:
    with conn.cursor() as cur:
        # documents 테이블 구조
        print('=== documents 테이블 ===')
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'documents'
        """)
        cols = cur.fetchall()
        print(f'컬럼: {[c[0] for c in cols]}')
        cur.execute("SELECT COUNT(*) FROM documents")
        print(f'총 레코드 수: {cur.fetchone()[0]}')
        cur.execute("SELECT * FROM documents LIMIT 2")
        for row in cur.fetchall():
            print(f'  샘플: {str(row)[:150]}')
        
        # work_history 테이블
        print('\n=== work_history 테이블 ===')
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'work_history'
        """)
        cols = cur.fetchall()
        print(f'컬럼: {[c[0] for c in cols]}')
        cur.execute("SELECT COUNT(*) FROM work_history")
        print(f'총 레코드 수: {cur.fetchone()[0]}')
        cur.execute("SELECT * FROM work_history LIMIT 2")
        for row in cur.fetchall():
            print(f'  샘플: {str(row)[:150]}')
        
        # maintenance_history 테이블
        print('\n=== maintenance_history 테이블 ===')
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'maintenance_history'
        """)
        cols = cur.fetchall()
        print(f'컬럼: {[c[0] for c in cols]}')
        cur.execute("SELECT COUNT(*) FROM maintenance_history")
        print(f'총 레코드 수: {cur.fetchone()[0]}')
        cur.execute("SELECT * FROM maintenance_history LIMIT 2")
        for row in cur.fetchall():
            print(f'  샘플: {str(row)[:150]}')
        
        # CI 샘플
        print('\n=== CI 샘플 ===')
        cur.execute("SELECT ci_code, ci_name, ci_type, status FROM ci LIMIT 5")
        for row in cur.fetchall():
            print(f'  code={row[0]}, name={row[1]}, type={row[2]}, status={row[3]}')
        
        # 이벤트 관련 CI 조회 (복합 쿼리 테스트용)
        print('\n=== 가장 많은 이벤트가 발생한 CI Top 5 ===')
        cur.execute("""
            SELECT c.ci_name, COUNT(e.id) as event_count 
            FROM ci c 
            JOIN event_log e ON c.ci_code = e.ci_code 
            GROUP BY c.ci_name 
            ORDER BY event_count DESC 
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]} events')
