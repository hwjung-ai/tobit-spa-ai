from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed.utils import get_postgres_conn

random.seed(1)

EVENT_TYPES = [
    "threshold_alarm",
    "status_change",
    "deployment",
    "health_check",
    "security_alert",
]

SOURCE_DISTRIBUTION = ["device"] * 7 + ["cep"] * 3
SEVERITY_BUCKETS = [1, 1, 2, 2, 2, 2, 3, 3, 4, 5]

START = datetime(2025, 12, 1, tzinfo=timezone.utc)
DAYS = 31
AVERAGE_PER_DAY = 1000


def main() -> None:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE event_log")
            cur.execute("SELECT ci_id, ci_code FROM ci")
            ci_targets = cur.fetchall()
            if not ci_targets:
                raise RuntimeError("No CI entries available for events")

            rows: list[tuple] = []
            for day_offset in range(DAYS):
                day_start = START + timedelta(days=day_offset)
                day_events = AVERAGE_PER_DAY + random.randint(-150, 150)
                for _ in range(day_events):
                    ts = day_start + timedelta(seconds=random.randint(0, 86_399))
                    ci_id, ci_code = random.choice(ci_targets)
                    severity = random.choice(SEVERITY_BUCKETS)
                    source = random.choice(SOURCE_DISTRIBUTION)
                    event_type = random.choice(EVENT_TYPES)
                    title = f"{event_type.replace('_', ' ').title()} detected"
                    message = f"{ci_code} reported {event_type} severity {severity}"
                    attributes = json.dumps(
                        {"ci_code": ci_code, "system": ci_code.split("-")[1]}
                    )
                    rows.append(
                        (
                            ts,
                            "t1",
                            str(ci_id),
                            event_type,
                            severity,
                            source,
                            title,
                            message,
                            attributes,
                        )
                    )
            insert_sql = """
                INSERT INTO event_log (
                    time, tenant_id, ci_id, event_type, severity,
                    source, title, message, attributes
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cur.executemany(insert_sql, rows)
        conn.commit()
    print(f"Inserted {len(rows)} event_log rows")


if __name__ == "__main__":
    main()
