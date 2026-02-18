#!/usr/bin/env python3
"""DB 실제 데이터 검증 스크립트 v3 - 세부 데이터"""
import psycopg

conn_str = "host=115.21.12.151 port=5432 dbname=spadb user=spa password=WeMB1! connect_timeout=10"

def run_query(query):
    try:
        with psycopg.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return rows
    except Exception as e:
        return f"ERROR: {e}"

# CI 컬럼 확인
print("=== CI 테이블 컬럼 ===")
r = run_query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='ci' ORDER BY ordinal_position")
for row in r:
    print(f"  {row[0]}: {row[1]}")

print("\n=== CI 샘플 (ERP 관련) ===")
r = run_query("SELECT * FROM ci LIMIT 3")
if isinstance(r, list) and r:
    print(f"  컬럼수: {len(r[0])}, 샘플: {r[0]}")

# ERP System 찾기
r = run_query("SELECT column_name FROM information_schema.columns WHERE table_name='ci'")
cols = [row[0] for row in r] if isinstance(r, list) else []
print(f"  CI 컬럼: {cols}")

# ci_name 또는 다른 이름 컬럼 찾기
for col in ['ci_name', 'name', 'label', 'display_name', 'title']:
    if col in cols:
        r2 = run_query(f"SELECT {col}, status, ci_type FROM ci WHERE {col} LIKE '%ERP%' LIMIT 5")
        print(f"  ERP CIs ({col}): {r2}")
        break

print("\n=== documents 테이블 컬럼 ===")
r = run_query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='documents' ORDER BY ordinal_position")
for row in r:
    print(f"  {row[0]}: {row[1]}")

print("\n=== documents 데이터 ===")
r = run_query("SELECT COUNT(*) FROM documents")
print(f"  total: {r[0][0] if isinstance(r, list) else r}")

# file_type 컬럼 확인
r = run_query("SELECT column_name FROM information_schema.columns WHERE table_name='documents'")
doc_cols = [row[0] for row in r] if isinstance(r, list) else []
print(f"  컬럼: {doc_cols}")

for col in ['file_type', 'type', 'mime_type', 'content_type', 'doc_type']:
    if col in doc_cols:
        r2 = run_query(f"SELECT {col}, COUNT(*) FROM documents GROUP BY {col} ORDER BY COUNT(*) DESC")
        print(f"  {col} 분포: {r2}")
        break

for col in ['file_size', 'size', 'content_length']:
    if col in doc_cols:
        r2 = run_query(f"SELECT MAX({col}), MIN({col}) FROM documents")
        print(f"  {col} max/min: {r2}")
        r3 = run_query(f"SELECT file_name, {col} FROM documents ORDER BY {col} DESC LIMIT 1")
        print(f"  최대 파일: {r3}")
        break

for col in ['category', 'doc_category', 'type']:
    if col in doc_cols:
        r2 = run_query(f"SELECT DISTINCT {col} FROM documents ORDER BY {col}")
        print(f"  카테고리 ({col}): {r2}")
        break

for col in ['status', 'process_status', 'state']:
    if col in doc_cols:
        r2 = run_query(f"SELECT {col}, COUNT(*) FROM documents GROUP BY {col}")
        print(f"  상태 ({col}): {r2}")
        break

print("\n=== work_history 컬럼 ===")
r = run_query("SELECT column_name FROM information_schema.columns WHERE table_name='work_history' ORDER BY ordinal_position")
wh_cols = [row[0] for row in r] if isinstance(r, list) else []
print(f"  컬럼: {wh_cols}")

for col in ['work_type', 'type', 'action_type']:
    if col in wh_cols:
        r2 = run_query(f"SELECT {col}, COUNT(*) FROM work_history GROUP BY {col} ORDER BY COUNT(*) DESC")
        print(f"  work_type 분포: {r2}")
        break

for col in ['result', 'status', 'outcome']:
    if col in wh_cols:
        r2 = run_query(f"SELECT {col}, COUNT(*) FROM work_history GROUP BY {col} ORDER BY COUNT(*) DESC")
        print(f"  result 분포: {r2}")
        break

print("\n=== maintenance_history 컬럼 ===")
r = run_query("SELECT column_name FROM information_schema.columns WHERE table_name='maintenance_history' ORDER BY ordinal_position")
mh_cols = [row[0] for row in r] if isinstance(r, list) else []
print(f"  컬럼: {mh_cols}")

for col in ['maintenance_type', 'type', 'action_type']:
    if col in mh_cols:
        r2 = run_query(f"SELECT {col}, COUNT(*) FROM maintenance_history GROUP BY {col} ORDER BY COUNT(*) DESC")
        print(f"  maintenance_type 분포: {r2}")
        break

for col in ['result', 'status', 'outcome']:
    if col in mh_cols:
        r2 = run_query(f"SELECT {col}, COUNT(*) FROM maintenance_history GROUP BY {col} ORDER BY COUNT(*) DESC")
        print(f"  result 분포: {r2}")
        break

print("\n=== tb_audit_log 개수 ===")
r = run_query("SELECT COUNT(*) FROM tb_audit_log")
print(f"  tb_audit_log: {r[0][0] if isinstance(r, list) else r}")

print("\nDB 검증 완료")
