#!/usr/bin/env python3
"""
최근 실행된 테스트 trace 분석
"""
import psycopg2
import json
from datetime import datetime, timedelta

def get_db_connection():
    return psycopg2.connect(
        host="115.21.12.151",
        port=5432,
        database="spadb",
        user="spa",
        password="WeMB1!"
    )

print("=" * 100)
print("최근 20개 테스트 Trace 상세 분석")
print("=" * 100)
print(f"실행 시간: {datetime.now().isoformat()}\n")

conn = get_db_connection()
cur = conn.cursor()

# Step 1: 최근 20개 Trace 조회
print("\n[Step 1] 최근 20개 Trace 조회")
print("-" * 100)

try:
    cur.execute("""
        SELECT
            trace_id,
            question,
            status,
            duration_ms,
            created_at,
            answer,
            stage_inputs
        FROM tb_execution_trace
        ORDER BY created_at DESC
        LIMIT 20
    """)

    traces = cur.fetchall()
    print(f"✓ {len(traces)}개의 최근 trace 발견\n")

    for idx, (trace_id, question, status, duration_ms, created_at, answer, stage_inputs) in enumerate(traces, 1):
        print(f"[Test #{idx}]")
        print(f"  Trace ID: {trace_id}")
        print(f"  Question: {question[:60]}..." if len(question or "") > 60 else f"  Question: {question}")
        print(f"  Status: {status}")
        print(f"  Duration: {duration_ms}ms")
        print(f"  Created: {created_at}")

        # Answer 분석
        if answer:
            answer_str = str(answer)[:100]
            print(f"  Answer: {answer_str}...")
        else:
            print(f"  Answer: None")

        # Stage inputs 분석
        if stage_inputs:
            try:
                stage_data = json.loads(stage_inputs) if isinstance(stage_inputs, str) else stage_inputs
                if isinstance(stage_data, dict):
                    print(f"  Stages: {len(stage_data)} 개")
                elif isinstance(stage_data, list):
                    print(f"  Stages: {len(stage_data)} 개")
                else:
                    print(f"  Stages: 데이터 형식 불명")
            except:
                print(f"  Stages: 파싱 실패")
        else:
            print(f"  Stages: None")

        print()

except Exception as e:
    print(f"ERROR: {str(e)}")

# Step 2: 상태별 분포
print("\n[Step 2] 상태별 분포 (최근 100개)")
print("-" * 100)

try:
    cur.execute("""
        SELECT status, COUNT(*) as count
        FROM tb_execution_trace
        WHERE created_at > NOW() - INTERVAL '1 hour'
        GROUP BY status
        ORDER BY count DESC
    """)

    results = cur.fetchall()
    total = sum(r[1] for r in results)

    for status, count in results:
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {status:15s}: {count:4d}개 ({pct:5.1f}%)")

except Exception as e:
    print(f"ERROR: {str(e)}")

# Step 3: 성능 분석
print("\n[Step 3] 성능 분석 (최근 100개)")
print("-" * 100)

try:
    cur.execute("""
        SELECT
            COUNT(*) as total,
            MIN(duration_ms) as min_duration,
            MAX(duration_ms) as max_duration,
            AVG(duration_ms) as avg_duration
        FROM tb_execution_trace
        WHERE created_at > NOW() - INTERVAL '1 hour'
    """)

    result = cur.fetchone()
    total, min_d, max_d, avg_d = result

    print(f"  총 테스트: {total}")
    print(f"  최소 응답시간: {min_d}ms")
    print(f"  최대 응답시간: {max_d}ms")
    print(f"  평균 응답시간: {avg_d:.0f}ms")

except Exception as e:
    print(f"ERROR: {str(e)}")

# Step 4: Applied Assets 분석 (최근 20개)
print("\n[Step 4] Applied Assets 분석 (최근 20개)")
print("-" * 100)

try:
    cur.execute("""
        SELECT
            applied_assets
        FROM tb_execution_trace
        ORDER BY created_at DESC
        LIMIT 20
    """)

    traces = cur.fetchall()

    # 모든 applied assets 수집
    all_assets = {}
    for (applied_assets,) in traces:
        if applied_assets:
            try:
                assets_data = json.loads(applied_assets) if isinstance(applied_assets, str) else applied_assets
                if isinstance(assets_data, dict):
                    for asset_name, asset_info in assets_data.items():
                        if asset_name not in all_assets:
                            all_assets[asset_name] = 0
                        all_assets[asset_name] += 1
                elif isinstance(assets_data, list):
                    for asset in assets_data:
                        if isinstance(asset, dict) and 'name' in asset:
                            name = asset['name']
                            if name not in all_assets:
                                all_assets[name] = 0
                            all_assets[name] += 1
            except:
                pass

    if all_assets:
        sorted_assets = sorted(all_assets.items(), key=lambda x: x[1], reverse=True)
        for asset_name, count in sorted_assets:
            print(f"  {asset_name:40s}: {count:2d}개 테스트에서 사용")
    else:
        print("  Applied assets 데이터 없음")

except Exception as e:
    print(f"ERROR: {str(e)}")

# Step 5: 구체적인 실패 분석
print("\n[Step 5] 실패 원인 분석")
print("-" * 100)

try:
    cur.execute("""
        SELECT status, COUNT(*) as count
        FROM tb_execution_trace
        GROUP BY status
    """)

    results = cur.fetchall()

    for status, count in results:
        print(f"  {status}: {count}개")

except Exception as e:
    print(f"ERROR: {str(e)}")

cur.close()
conn.close()

print("\n" + "=" * 100)
print("분석 완료")
print("=" * 100)
