#!/usr/bin/env python3
"""
간단한 진단 스크립트: 각 쿼리마다 새로운 연결 사용
"""
import psycopg2
import json
from datetime import datetime

def run_query(sql, description=""):
    """각 쿼리마다 새로운 연결 생성"""
    conn = psycopg2.connect(
        host="115.21.12.151",
        port=5432,
        database="spadb",
        user="spa",
        password="WeMB1!"
    )
    cur = conn.cursor()
    try:
        cur.execute(sql)
        result = cur.fetchall()
        conn.commit()
        return result
    except Exception as e:
        return None, str(e)
    finally:
        cur.close()
        conn.close()

print("=" * 80)
print("데이터베이스 진단 보고서 (간단 버전)")
print("=" * 80)
print(f"실행 시간: {datetime.now().isoformat()}\n")

# Step 1: 핵심 테이블 데이터 확인
print("\n[Step 1] 핵심 테이블 데이터 개수")
print("-" * 80)

tables = ["ci", "ci_ext", "event_log", "tb_asset_registry", "tb_execution_trace", "assets"]

for table in tables:
    result = run_query(f"SELECT COUNT(*) FROM {table}")
    if isinstance(result, list):
        count = result[0][0] if result else 0
        print(f"  {table:30s}: {count:,} 건")
    else:
        print(f"  {table:30s}: ERROR")

# Step 2: Published Assets 확인
print("\n[Step 2] Published Assets 확인")
print("-" * 80)

result = run_query("""
    SELECT asset_type, COUNT(*) as count
    FROM tb_asset_registry
    WHERE status = 'published'
    GROUP BY asset_type
    ORDER BY count DESC
""")

if isinstance(result, list) and result:
    total = sum(r[1] for r in result)
    for asset_type, count in result:
        print(f"  {asset_type:30s}: {count:3d} 개")
    print(f"  {'=' * 50}")
    print(f"  {'합계':30s}: {total:3d} 개")
else:
    print("  Published asset이 없습니다")

# Step 3: 최근 Trace 확인
print("\n[Step 3] 최근 5개 Execution Trace")
print("-" * 80)

result = run_query("""
    SELECT trace_id, question, created_at, status, duration_ms
    FROM tb_execution_trace
    ORDER BY created_at DESC
    LIMIT 5
""")

if isinstance(result, list) and result:
    for trace_id, question, created_at, status, duration_ms in result:
        q_short = (str(question)[:40] + "...") if question and len(str(question)) > 40 else question
        print(f"  [{status:10s}] {duration_ms:6d}ms | {q_short}")
else:
    print("  Trace 데이터 없음")

# Step 4: 진단 요약
print("\n[Step 4] 진단 요약")
print("-" * 80)

# CI 데이터 확인
ci_result = run_query("SELECT COUNT(*) FROM ci")
ci_count = ci_result[0][0] if isinstance(ci_result, list) and ci_result else 0

# Asset 확인
asset_result = run_query("SELECT COUNT(*) FROM tb_asset_registry WHERE status = 'published'")
asset_count = asset_result[0][0] if isinstance(asset_result, list) and asset_result else 0

# Trace 확인
trace_result = run_query("SELECT COUNT(*) FROM tb_execution_trace")
trace_count = trace_result[0][0] if isinstance(trace_result, list) and trace_result else 0

print(f"✓ CI 데이터: {ci_count:,} 건")
print(f"✓ Published Assets: {asset_count:,} 개")
print(f"✓ Execution Traces: {trace_count:,} 건")

print("\n[진단 결론]")
if ci_count == 0:
    print("⚠ 경고 #1: CI 데이터가 없습니다")
    print("  → 이것이 테스트에서 '0건' 결과를 반환하는 이유입니다")
    print("  → API는 정상 동작하지만, 쿼리할 데이터가 없습니다")
else:
    print(f"✓ CI 데이터가 {ci_count:,}건 있습니다")

if asset_count == 0:
    print("⚠ 경고 #2: Published asset이 없습니다")
else:
    print(f"✓ Published asset이 {asset_count:,}개 있습니다")

if trace_count > 0:
    print(f"✓ 실행 trace가 {trace_count:,}개 기록되어 있습니다")

print("\n" + "=" * 80)
print("진단 완료")
print("=" * 80)
