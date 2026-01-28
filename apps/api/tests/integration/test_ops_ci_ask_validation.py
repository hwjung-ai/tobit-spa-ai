"""
실제 ops/ci/ask API를 통한 통합 테스트
Trace ID 기반 상세 분석 및 검증
"""

import json
import asyncio
import httpx
from datetime import datetime

# 테스트 설정
API_BASE_URL = "http://localhost:8000"
TRACE_ID = "7a3e39d9-1b32-4e93-be11-cc3ad4a820e1"

async def test_ops_ci_ask_real_query():
    """
    실제 LLM 기반 질의 테스트
    ops/ci/ask 엔드포인트를 직접 호출
    """
    async with httpx.AsyncClient(timeout=60) as client:
        payload = {
            "question": "시스템의 현재 상태를 알려줘",
            "mode": "real"
        }

        print("\n" + "="*80)
        print("📍 실제 ops/ci/ask API 테스트")
        print("="*80)
        print(f"엔드포인트: POST {API_BASE_URL}/ops/ci/ask")
        print(f"질의: {payload['question']}")
        print()

        try:
            response = await client.post(
                f"{API_BASE_URL}/ops/ci/ask",
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 요청 성공")
                print(f"\n응답 구조:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])

                # Trace 정보 추출
                if 'data' in data and 'trace_id' in data['data']:
                    trace_id = data['data']['trace_id']
                    print(f"\n생성된 Trace ID: {trace_id}")

                    # Trace 상세 조회
                    await test_trace_details(client, trace_id)

            else:
                print(f"❌ 오류: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ 예외: {e}")


async def test_trace_details(client, trace_id: str):
    """
    특정 Trace의 상세 정보 조회
    Stage별 소요시간과 Asset 확인
    """
    print("\n" + "-"*80)
    print(f"🔍 Trace 상세 분석 (ID: {trace_id})")
    print("-"*80)

    try:
        response = await client.get(
            f"{API_BASE_URL}/inspector/traces/{trace_id}"
        )

        if response.status_code == 200:
            trace = response.json()

            # 기본 정보
            print(f"상태: {trace.get('status')}")
            print(f"전체 소요시간: {trace.get('duration_ms')}ms")
            print(f"생성 시간: {trace.get('created_at')}")

            # Stage별 분석
            stage_inputs = trace.get('stage_inputs', [])
            print(f"\n📊 Stage 분석 ({len(stage_inputs)}개):")
            print()

            total_stage_time = 0
            for idx, stage in enumerate(stage_inputs, 1):
                stage_name = stage.get('stage', f'stage_{idx}')
                inputs = stage.get('inputs', {})
                outputs = stage.get('outputs', {})
                elapsed = outputs.get('elapsed_ms', 0) if outputs else 0

                print(f"Stage {idx}: {stage_name}")
                print(f"  ├─ 소요시간: {elapsed}ms")
                print(f"  ├─ 입력: {json.dumps(inputs, ensure_ascii=False)[:100]}")
                print(f"  ├─ 출력: {json.dumps(outputs, ensure_ascii=False)[:100]}")

                # Applied Assets 분석
                applied = stage.get('applied_assets', {})
                if applied:
                    print(f"  └─ 적용된 Asset ({len(applied)}개):")
                    for asset_type, asset_info in applied.items():
                        if asset_info:
                            name = asset_info if isinstance(asset_info, str) else asset_info.get('name', '?')
                            print(f"     - {asset_type}: {name}")
                else:
                    print(f"  └─ 적용된 Asset: 없음")
                print()

                total_stage_time += elapsed

            print(f"Stage 전체 소요시간: {total_stage_time}ms")

            # Applied Assets 최상위
            applied_assets = trace.get('applied_assets', {})
            if applied_assets:
                print(f"\n📦 전체 적용된 Asset ({len(applied_assets)}개):")
                for asset_type, asset_info in applied_assets.items():
                    if asset_info:
                        print(f"  - {asset_type}: {asset_info}")

        else:
            print(f"❌ 오류: {response.status_code}")

    except Exception as e:
        print(f"❌ 예외: {e}")


async def test_catalog_assets():
    """
    실제 Catalog Asset 조회
    """
    import psycopg2

    print("\n" + "="*80)
    print("📚 Catalog Asset 조회")
    print("="*80)

    try:
        conn = psycopg2.connect(
            host="115.21.12.151",
            port=5432,
            database="spadb",
            user="spa",
            password="WeMB1!"
        )

        cursor = conn.cursor()

        # Catalog 조회
        cursor.execute("""
            SELECT
                asset_id,
                name,
                version,
                status,
                created_at
            FROM tb_asset_registry
            WHERE asset_type = 'catalog'
            ORDER BY created_at DESC
        """)

        catalogs = cursor.fetchall()
        print(f"\n발견된 Catalog: {len(catalogs)}개")

        for catalog in catalogs:
            print(f"  - {catalog[1]} (v{catalog[2]}, {catalog[3]})")
            print(f"    ID: {catalog[0]}")
            print(f"    생성: {catalog[4]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ DB 연결 오류: {e}")


async def test_stage_specific_assets():
    """
    실제 Stage별 Asset 분석
    DB에서 직접 stage_inputs 조회
    """
    import psycopg2
    import json as json_lib

    print("\n" + "="*80)
    print("⚙️ Stage별 Asset 상세 분석")
    print("="*80)

    trace_id = TRACE_ID

    try:
        conn = psycopg2.connect(
            host="115.21.12.151",
            port=5432,
            database="spadb",
            user="spa",
            password="WeMB1!"
        )

        cursor = conn.cursor()

        # Trace 조회
        cursor.execute("""
            SELECT
                trace_id,
                status,
                duration_ms,
                stage_inputs,
                applied_assets
            FROM tb_execution_trace
            WHERE trace_id = %s
        """, (trace_id,))

        result = cursor.fetchone()

        if result:
            trace_id, status, duration_ms, stage_inputs, applied_assets = result

            print(f"\nTrace: {trace_id}")
            print(f"상태: {status}, 총 소요시간: {duration_ms}ms")

            # Stage별 분석
            if stage_inputs:
                print(f"\n📋 Stage별 상세 분석:")
                print()

                for idx, stage_data in enumerate(stage_inputs, 1):
                    if isinstance(stage_data, dict):
                        stage = stage_data.get('stage', f'stage_{idx}')
                        assets = stage_data.get('applied_assets', {})
                        inputs = stage_data.get('inputs', {})
                        outputs = stage_data.get('outputs', {})

                        # 이 stage에서만 사용되는 asset 찾기
                        if isinstance(assets, dict) and assets:
                            print(f"Stage {idx}: {stage}")
                            print(f"  소요시간: {outputs.get('elapsed_ms', 'N/A')}ms" if outputs else "  소요시간: N/A")
                            print(f"  적용된 Asset ({len(assets)}개):")
                            for asset_type, asset_info in assets.items():
                                if asset_info:
                                    print(f"    • {asset_type}: {asset_info}")
                            print()
                        else:
                            print(f"Stage {idx}: {stage} (Asset 없음)")
                            print()

            # 전체 applied assets
            print(f"\n📦 전체 적용된 Asset:")
            if applied_assets:
                for asset_type, asset_info in applied_assets.items():
                    if asset_info:
                        print(f"  - {asset_type}: {asset_info}")
            else:
                print("  없음")
        else:
            print(f"Trace {trace_id}를 찾을 수 없습니다.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ DB 오류: {e}")


async def main():
    """메인 테스트 실행"""

    # 1. Catalog 확인
    await test_catalog_assets()

    # 2. 실제 Stage 분석
    await test_stage_specific_assets()

    # 3. LLM 기반 질의 테스트 (시간이 걸릴 수 있음)
    print("\n" + "="*80)
    print("⚠️  LLM 기반 질의 테스트는 시간이 걸립니다.")
    print("실행하시겠습니까? (y/n): ", end="")

    # 자동으로 테스트 실행 (수동 입력 불가 환경)
    try:
        await test_ops_ci_ask_real_query()
    except Exception as e:
        print(f"LLM 테스트 오류: {e}")


if __name__ == "__main__":
    asyncio.run(main())
