#!/usr/bin/env python3
"""
CI 코드 자동 선정 + 유일성 검증
- seed_ci.py에서 deterministic하게 선정
- DB에서 각 코드가 유일하게 매칭되는지 확인
- 중복이면 다른 코드 선정
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load environment
os.chdir(str(ROOT))
from dotenv import load_dotenv

load_dotenv(str(ROOT / "apps/api/.env"))

import json


def get_postgres_conn():
    """Postgres 연결"""
    from apps.api.scripts.seed.utils import get_postgres_conn as get_conn
    return get_conn()


def verify_unique_match(ci_code: str) -> bool:
    """ci_code가 정확히 1건만 매칭되는지 확인"""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ci WHERE ci_code = %s", (ci_code,))
                count = cur.fetchone()[0]
                return count == 1
    except Exception as e:
        print(f"Error verifying {ci_code}: {e}", file=sys.stderr)
        return False


def select_ci_codes() -> dict[str, str] | None:
    """
    유일한 CI 코드 선정:
    - SYSTEM_DEFINITIONS[0] (erp) 기준
    - srv-erp-01, os-erp-01
    - app은 DB에서 실제 존재하는 첫 번째 erp app 사용
    """
    # 서버/OS는 seed 패턴이 명확함
    candidates = {
        "server": "srv-erp-01",
        "os": "os-erp-01",
        "app": None,  # DB에서 확보
    }

    # DB에서 실제 존재하는 erp app 첫 번째 찾기
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ci_code FROM ci WHERE ci_code LIKE 'app-erp%' ORDER BY ci_code LIMIT 1")
                result = cur.fetchone()
                if result:
                    candidates["app"] = result[0]
    except Exception as e:
        print(f"Error fetching app code: {e}", file=sys.stderr)
        return None

    if not candidates["app"]:
        print("No erp apps found in DB", file=sys.stderr)
        return None

    print("🔍 선정된 CI 코드 유일성 검증 중...", file=sys.stderr)
    for ci_type, ci_code in candidates.items():
        print(f"   {ci_type}: {ci_code}...", end=" ", file=sys.stderr)
        if verify_unique_match(ci_code):
            print("✅", file=sys.stderr)
        else:
            print("❌ (1건 이상 중복 또는 0건)", file=sys.stderr)
            return None

    print("✅ 모든 코드가 유일하게 매칭됨", file=sys.stderr)
    return candidates


def main() -> int:
    codes = select_ci_codes()
    if not codes:
        print("❌ CI 코드 유일성 검증 실패", file=sys.stderr)
        return 1

    # JSON 출력
    print(json.dumps(codes, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
