#!/usr/bin/env python3
"""
진단 스크립트: 실제 DB 데이터 검증
"""
import psycopg2
import json
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host="115.21.12.151",
    port=5432,
    database="spadb",
    user="spa",
    password="WeMB1!"
)

print("=" * 80)
print("데이터베이스 진단 보고서")
print("=" * 80)
print(f"실행 시간: {datetime.now().isoformat()}\n")

# Step 1: 모든 테이블 확인
print("\n[Step 0] 사용 가능한 테이블 확인")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tables = [row[0] for row in cur.fetchall()]
    print(f"✓ 총 {len(tables)}개의 테이블이 있습니다:\n")

    for table in sorted(tables):
        print(f"  - {table}")
except Exception as e:
    print(f"  ERROR: {str(e)}")

cur.close()

# Step 1: 실제 데이터가 있는지 확인
print("\n[Step 1] 테이블별 데이터 개수 확인")
print("-" * 80)

tables_to_check = [
    "tb_ci",
    "tb_query",
    "tb_metric",
    "tb_asset_registry",
    "tb_execution_trace",
    "tb_stage_input",
    "tb_cep_event",
    "tb_api_log",
    "ci",
    "event_log"
]

for table_name in tables_to_check:
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        print(f"✓ {table_name:30s}: {count:,} 건")
    except psycopg2.errors.UndefinedTable:
        print(f"✗ {table_name:30s}: 테이블 없음")
    except Exception as e:
        print(f"✗ {table_name:30s}: ERROR - {str(e)[:40]}")
    finally:
        cur.close()

# Step 2: Asset Registry 현황
print("\n[Step 2] Asset Registry 현황 (published 상태)")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT asset_type, COUNT(*) as count
        FROM tb_asset_registry
        WHERE status = 'published'
        GROUP BY asset_type
        ORDER BY asset_type
    """)

    results = cur.fetchall()
    if results:
        for asset_type, count in results:
            print(f"  {asset_type:20s}: {count:3d} 개")
    else:
        print("  Published 상태의 asset이 없습니다")
except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 3: 문제 asset 확인
print("\n[Step 3] 주요 Asset 목록 (query, mapping, prompt, policy)")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT asset_type, name, version, status
        FROM tb_asset_registry
        WHERE asset_type IN ('query', 'mapping', 'prompt', 'policy')
        ORDER BY asset_type, name
    """)

    results = cur.fetchall()
    if results:
        for asset_type, name, version, status in results:
            print(f"  [{status:9s}] {asset_type:10s} | {name:40s} | v{version}")
    else:
        print("  해당 asset이 없습니다")
except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 4: 최근 Trace 확인
print("\n[Step 4] 최근 10개 Execution Trace")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT
            trace_id,
            question,
            created_at,
            duration_ms,
            status
        FROM tb_execution_trace
        ORDER BY created_at DESC
        LIMIT 10
    """)

    results = cur.fetchall()
    if results:
        for trace_id, question, created_at, duration_ms, status in results:
            q_short = (question[:50] + "...") if len(question or "") > 50 else question
            print(f"  [{status:10s}] {trace_id[:8]}... | {duration_ms:6d}ms | {q_short}")
    else:
        print("  Trace 데이터가 없습니다")
except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 5: Stage Input 현황
print("\n[Step 5] Stage Input 현황")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT
            stage_name,
            COUNT(*) as count,
            AVG(duration_ms) as avg_duration,
            MAX(duration_ms) as max_duration
        FROM tb_stage_input
        GROUP BY stage_name
        ORDER BY stage_name
    """)

    results = cur.fetchall()
    if results:
        for stage_name, count, avg_duration, max_duration in results:
            print(f"  {stage_name:20s}: {count:4d} 건 | 평균: {avg_duration or 0:6.0f}ms | 최대: {max_duration or 0:6.0f}ms")
    else:
        print("  Stage Input 데이터가 없습니다")
except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 6: 기본 데이터 소스 확인
print("\n[Step 6] 기본 데이터 소스 확인 (primary_postgres)")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT name, asset_type, status, config
        FROM tb_asset_registry
        WHERE name = 'primary_postgres' AND status = 'published'
    """)

    result = cur.fetchone()
    if result:
        name, asset_type, status, config = result
        print(f"✓ Primary Postgres Source: {status}")
        if config:
            try:
                config_dict = json.loads(config) if isinstance(config, str) else config
                print(f"  설정:")
                for key, value in config_dict.items():
                    if key != 'password':
                        print(f"    {key}: {value}")
                    else:
                        print(f"    {key}: ****")
            except:
                print(f"  설정: {config}")
    else:
        print("✗ Primary Postgres Source not found or not published")
except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 7: 현재 사용 가능한 모든 published asset
print("\n[Step 7] 모든 Published Assets")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT asset_type, COUNT(*) as count
        FROM tb_asset_registry
        WHERE status = 'published'
        GROUP BY asset_type
        ORDER BY count DESC
    """)

    results = cur.fetchall()
    if results:
        total = sum(count for _, count in results)
        for asset_type, count in results:
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {asset_type:20s}: {count:3d} 개 ({pct:5.1f}%)")
        print(f"  {'=' * 40}")
        print(f"  {'합계':20s}: {total:3d} 개")
    else:
        print("  Published asset이 없습니다")
except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 8: CI 데이터 샘플 확인
print("\n[Step 8] CI 데이터 확인")
print("-" * 80)

cur = conn.cursor()
try:
    # ci 테이블 확인
    cur.execute("""
        SELECT COUNT(*) FROM ci
    """)

    count = cur.fetchone()[0]
    print(f"  ci 테이블: {count:,} 건")

    if count > 0:
        # 샘플 데이터 확인
        cur.execute("SELECT * FROM ci LIMIT 3")
        rows = cur.fetchall()

        # 컬럼 정보 확인
        col_names = [desc[0] for desc in cur.description]
        print(f"  컬럼 ({len(col_names)}개): {', '.join(col_names[:5])}...")

except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 9: CI_ext 데이터 확인
print("\n[Step 9] CI_ext 데이터 확인")
print("-" * 80)

cur = conn.cursor()
try:
    cur.execute("""
        SELECT COUNT(*) FROM ci_ext
    """)

    count = cur.fetchone()[0]
    print(f"  ci_ext 테이블: {count:,} 건")

except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

# Step 10: 진단 요약
print("\n[Step 10] 진단 요약")
print("-" * 80)

cur = conn.cursor()
try:
    # CI 데이터 확인
    cur.execute("SELECT COUNT(*) FROM ci")
    ci_count = cur.fetchone()[0]

    # Asset 확인
    cur.execute("SELECT COUNT(*) FROM tb_asset_registry WHERE status = 'published'")
    asset_count = cur.fetchone()[0]

    # Trace 확인
    cur.execute("SELECT COUNT(*) FROM tb_execution_trace")
    trace_count = cur.fetchone()[0]

    print(f"✓ 데이터베이스 연결: 정상")
    print(f"✓ CI 데이터: {ci_count:,} 건")
    print(f"✓ Published Assets: {asset_count:,} 개")
    print(f"✓ Execution Traces: {trace_count:,} 건")

    print("\n[진단 결과]")
    if ci_count == 0:
        print("⚠ 경고 #1: CI 데이터가 없습니다")
        print("  → 이것이 테스트 실패의 주요 원인입니다")
        print("  → API는 'No CI matches found' 응답을 반환합니다")
    else:
        print(f"✓ CI 데이터가 {ci_count:,}건 있습니다 - 정상")

    if asset_count == 0:
        print("⚠ 경고 #2: Published asset이 없습니다")
        print("  → 시스템이 제대로 동작하지 않을 수 있습니다")
    else:
        print(f"✓ Published asset이 {asset_count:,}개 있습니다 - 정상")

    if trace_count == 0:
        print("⚠ 경고 #3: 실행 trace 데이터가 없습니다")
    else:
        print(f"✓ 실행 trace가 {trace_count:,}개 있습니다 - 정상")

except Exception as e:
    print(f"  ERROR: {str(e)}")
finally:
    cur.close()

conn.close()

print("\n" + "=" * 80)
print("진단 완료")
print("=" * 80)
