#!/usr/bin/env python3
"""DB 실제 데이터 조회하여 다양한 테스트 케이스용 데이터 확보"""

import psycopg

conn_str = 'host=115.21.12.151 port=5432 dbname=spadb user=spa password=WeMB1!'

with psycopg.connect(conn_str, connect_timeout=10) as conn:
    with conn.cursor() as cur:
        # CI 상태 분포
        print('=== CI 상태 분포 ===')
        cur.execute("SELECT status, COUNT(*) FROM ci GROUP BY status ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # 이벤트 유형 분포
        print('\n=== 이벤트 유형 분포 ===')
        cur.execute("SELECT event_type, COUNT(*) FROM event_log GROUP BY event_type ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # 최근 이벤트 상세
        print('\n=== 최근 이벤트 5개 ===')
        cur.execute("""
            SELECT event_type, time, severity 
            FROM event_log 
            ORDER BY time DESC 
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f'  type={row[0]}, time={row[1]}, severity={row[2]}')
        
        # 심각도별 이벤트
        print('\n=== 심각도별 이벤트 분포 ===')
        cur.execute("SELECT severity, COUNT(*) FROM event_log GROUP BY severity ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # work_history 유형
        print('\n=== 작업 유형 분포 ===')
        cur.execute("SELECT work_type, COUNT(*) FROM work_history GROUP BY work_type ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # work_history 결과
        print('\n=== 작업 결과 분포 ===')
        cur.execute("SELECT result, COUNT(*) FROM work_history GROUP BY result ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # maintenance 유형
        print('\n=== 유지보수 유형 분포 ===')
        cur.execute("SELECT maint_type, COUNT(*) FROM maintenance_history GROUP BY maint_type ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # maintenance 결과
        print('\n=== 유지보수 결과 분포 ===')
        cur.execute("SELECT result, COUNT(*) FROM maintenance_history GROUP BY result ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # documents 상세
        print('\n=== 문서 유형 분포 ===')
        cur.execute("SELECT content_type, COUNT(*) FROM documents GROUP BY content_type")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # documents 카테고리
        print('\n=== 문서 카테고리 ===')
        cur.execute("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL LIMIT 10")
        for row in cur.fetchall():
            print(f'  {row[0]}')
        
        # 특정 CI 이름들
        print('\n=== CI 이름 예시 (다양한 유형) ===')
        cur.execute("""
            SELECT ci_name, ci_type, status 
            FROM ci 
            WHERE ci_type IN ('SYSTEM', 'HW', 'SW')
            LIMIT 10
        """)
        for row in cur.fetchall():
            print(f'  {row[0]} ({row[1]}): {row[2]}')
        
        # 메트릭 이름 예시
        print('\n=== 메트릭 이름 예시 ===')
        cur.execute("SELECT metric_name FROM metrics LIMIT 10")
        for row in cur.fetchall():
            print(f'  {row[0]}')
        
        # 평균 작업 시간
        print('\n=== 작업/유지보수 평균 시간 ===')
        cur.execute("SELECT AVG(duration_min) FROM work_history WHERE duration_min IS NOT NULL")
        print(f'  작업 평균: {cur.fetchone()[0]:.1f}분')
        cur.execute("SELECT AVG(duration_min) FROM maintenance_history WHERE duration_min IS NOT NULL")
        print(f'  유지보수 평균: {cur.fetchone()[0]:.1f}분')
        
        # 가장 큰 문서
        print('\n=== 가장 큰 문서 ===')
        cur.execute("SELECT filename, size FROM documents ORDER BY size DESC LIMIT 3")
        for row in cur.fetchall():
            print(f'  {row[0]}: {row[1]:,} bytes')