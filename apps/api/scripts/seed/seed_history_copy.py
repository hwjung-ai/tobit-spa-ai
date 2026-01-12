from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed.utils import get_postgres_conn

random.seed(2)

MAINT_TYPES = ["patch", "inspection", "capacity", "reboot"]
WORK_TYPES = ["deployment", "integration", "audit", "upgrade"]
PERFORMERS = ["infra-team", "platform-ops", "secops-team", "automation-team"]
RESULTS = ["success", "success", "degraded", "success"]
USERS = ["alice", "bob", "carl", "dana", "emma"]

YEAR_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
YEAR_END = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
DECEMBER_START = datetime(2025, 12, 1, tzinfo=timezone.utc)
DECEMBER_END = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def _random_window() -> tuple[datetime, datetime]:
    if random.random() < 0.4:
        base = DECEMBER_START
        span = int((DECEMBER_END - DECEMBER_START).total_seconds())
    else:
        base = YEAR_START
        span = int((YEAR_END - YEAR_START).total_seconds())
    offset = random.randint(0, span)
    start = base + timedelta(seconds=offset)
    duration = random.randint(30, 240)
    end = start + timedelta(minutes=duration)
    return start, end


def main() -> None:
    maint_count = random.randint(500, 1500)
    work_count = random.randint(1500, 4000)

    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE maintenance_history, work_history")
            cur.execute("SELECT ci_id FROM ci")
            ci_list = [row[0] for row in cur.fetchall()]
            if not ci_list:
                raise RuntimeError("CI table is empty")

            maint_rows: list[tuple] = []
            for _ in range(maint_count):
                ci_id = random.choice(ci_list)
                start, end = _random_window()
                duration = int((end - start).total_seconds() // 60)
                maint_rows.append(
                    (
                        str(uuid.uuid4()),
                        "t1",
                        str(ci_id),
                        random.choice(MAINT_TYPES),
                        "Routine maintenance",
                        "Automated job executed",
                        start,
                        end,
                        duration,
                        random.choice(PERFORMERS),
                        random.choice(RESULTS),
                        end,
                    )
                )

            work_rows: list[tuple] = []
            for _ in range(work_count):
                ci_id = random.choice(ci_list)
                start, end = _random_window()
                duration = int((end - start).total_seconds() // 60)
                work_rows.append(
                    (
                        str(uuid.uuid4()),
                        "t1",
                        str(ci_id),
                        random.choice(WORK_TYPES),
                        "Scheduled change",
                        "Automated workflow",
                        random.choice(USERS),
                        random.choice(USERS),
                        random.randint(1, 5),
                        start,
                        end,
                        duration,
                        random.choice(RESULTS),
                        end,
                    )
                )

            maint_sql = """
                INSERT INTO maintenance_history (
                    id, tenant_id, ci_id, maint_type, summary,
                    detail, start_time, end_time, duration_min,
                    performer, result, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cur.executemany(maint_sql, maint_rows)

            work_sql = """
                INSERT INTO work_history (
                    id, tenant_id, ci_id, work_type, summary,
                    detail, requested_by, approved_by, impact_level,
                    start_time, end_time, duration_min, result, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cur.executemany(work_sql, work_rows)
        conn.commit()

    print(f"Inserted {len(maint_rows)} maintenance and {len(work_rows)} work rows")


if __name__ == "__main__":
    main()
