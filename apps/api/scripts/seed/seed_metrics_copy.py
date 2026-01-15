from __future__ import annotations

import json
import math
import random
import uuid
from datetime import datetime, timedelta, timezone

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed.utils import get_postgres_conn

random.seed(0)

METRIC_DEFINITIONS = [
    {
        "name": "temperature",
        "unit": "C",
        "description": "Server chassis temperature",
        "value_type": "gauge",
    },
    {
        "name": "cpu_usage",
        "unit": "%",
        "description": "CPU utilization",
        "value_type": "gauge",
    },
    {
        "name": "memory_usage",
        "unit": "%",
        "description": "Memory utilization",
        "value_type": "gauge",
    },
    {
        "name": "disk_io",
        "unit": "ops",
        "description": "Disk I/O operations",
        "value_type": "counter",
    },
    {
        "name": "network_in",
        "unit": "MB",
        "description": "Network ingress",
        "value_type": "counter",
    },
]

METRIC_PATTERN = {
    "temperature": {"base": 38, "amp": 3},
    "cpu_usage": {"base": 40, "amp": 20},
    "memory_usage": {"base": 55, "amp": 15},
    "disk_io": {"base": 200, "amp": 120},
    "network_in": {"base": 80, "amp": 90},
}

START = datetime(2026, 1, 2, tzinfo=timezone.utc)
END = datetime(2026, 2, 1, tzinfo=timezone.utc)
METRIC_RESOLUTION = timedelta(minutes=1)
PEAK_WINDOWS = [12, 23]


def main() -> None:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE metric_value, metric_def")

            metric_rows = []
            for metric in METRIC_DEFINITIONS:
                metric_id = uuid.uuid4()
                metric_rows.append(
                    (
                        str(metric_id),
                        metric["name"],
                        metric["unit"],
                        metric["description"],
                        metric["value_type"],
                        datetime.now(timezone.utc),
                    )
                )
            insert_sql = """
                INSERT INTO metric_def (metric_id, metric_name, unit, description, value_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_sql, metric_rows)

            metric_map = {name: uuid for uuid, name, *_ in metric_rows}

            cur.execute(
                "SELECT ci_id, ci_code FROM ci WHERE ci_type = 'HW' AND ci_subtype = 'server' ORDER BY ci_code LIMIT 30"
            )
            server_targets = cur.fetchall()
            cur.execute(
                "SELECT ci_id, ci_code FROM ci WHERE ci_type = 'SW' AND ci_subtype IN ('os','db','was','web','app') ORDER BY ci_code LIMIT 20"
            )
            sw_targets = cur.fetchall()

            if len(server_targets) < 30 or len(sw_targets) < 20:
                raise RuntimeError("Not enough CI rows to generate metrics")

            targets = server_targets + sw_targets

            with cur.copy(
                "COPY metric_value (time, tenant_id, ci_id, metric_id, value, quality, tags) FROM STDIN"
            ) as copier:
                current = START
                while current < END:
                    minute_fraction = (current - START).total_seconds() / 3600
                    for ci_id, ci_code in targets:
                        system_code = ci_code.split("-")[1]
                        for metric in METRIC_DEFINITIONS:
                            profile = METRIC_PATTERN[metric["name"]]
                            base = profile["base"]
                            amp = profile["amp"]
                            variation = math.sin(2 * math.pi * minute_fraction / 24)
                            peak = 5 if current.hour in PEAK_WINDOWS else 0
                            noise = random.uniform(-0.5, 0.5)
                            value = max(0.0, base + amp * (variation + peak / 10) + noise)
                            quality = "good" if noise > -0.4 else "noisy"
                            tags = json.dumps({"system": system_code, "source": "ops_sim"})
                            copier.write_row(
                                (
                                    current,
                                    "t1",
                                    str(ci_id),
                                    str(metric_map[metric["name"]]),
                                    value,
                                    quality,
                                    tags,
                                )
                            )
                    current += METRIC_RESOLUTION

        conn.commit()

    print("Seeded metric_value for December 2025")


if __name__ == "__main__":
    main()
