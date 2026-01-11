from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed.utils import get_postgres_conn

random.seed(0)

SYSTEM_DEFINITIONS = [
    {
        "code": "erp",
        "name": "ERP",
        "subtype": "business_system",
        "category": "business",
        "owner": "erp-platform",
        "depends_on": ["cmdb", "apm"],
    },
    {
        "code": "mes",
        "name": "MES",
        "subtype": "control_system",
        "category": "manufacturing",
        "owner": "mes-ops",
        "depends_on": ["erp", "scada"],
    },
    {
        "code": "scada",
        "name": "SCADA",
        "subtype": "control_system",
        "category": "industrial",
        "owner": "scada-ops",
        "depends_on": ["mes"],
    },
    {
        "code": "mon",
        "name": "MON",
        "subtype": "monitoring_system",
        "category": "observability",
        "owner": "mon-ops",
        "depends_on": ["scada", "apm"],
    },
    {
        "code": "analytics",
        "name": "Analytics",
        "subtype": "business_system",
        "category": "insights",
        "owner": "analytics-ops",
        "depends_on": ["erp", "mes"],
    },
    {
        "code": "cmdb",
        "name": "CMDB",
        "subtype": "business_system",
        "category": "infra",
        "owner": "cmdb-ops",
        "depends_on": ["mon", "apm"],
    },
    {
        "code": "apm",
        "name": "APM",
        "subtype": "monitoring_system",
        "category": "observability",
        "owner": "apm-ops",
        "depends_on": ["cmdb", "mon"],
    },
    {
        "code": "secops",
        "name": "SECOPS",
        "subtype": "monitoring_system",
        "category": "security",
        "owner": "secops-team",
        "depends_on": ["mon", "apm"],
    },
]

ZONE_OPTIONS = ["zone-a", "zone-b", "zone-c"]
NETWORK_VENDORS = ["cisco", "arista", "juniper"]
STORAGE_RAIDS = ["RAID1", "RAID10", "RAID6"]
DB_ENGINES = ["postgres", "timescaledb", "cockroach"]
WAS_ENGINES = ["uvicorn", "gunicorn", "tomcat"]
WEB_ENGINES = ["nginx", "haproxy", "caddy"]
APP_LANGUAGES = ["python", "java", "nodejs", "go"]
APP_NAMES = [
    "order",
    "inventory",
    "pricing",
    "report",
    "alert",
    "integration",
    "audit",
    "scheduler",
]

CI_CATEGORY_MAP = {
    "SYSTEM": "business",
    "HW": "infrastructure",
    "SW": "application",
}


def build_ci_row(ci_id: uuid.UUID, **kwargs: Any) -> tuple:
    created = kwargs.get("created_at") or datetime.now(timezone.utc)
    updated = kwargs.get("updated_at") or created
    return (
        str(ci_id),
        kwargs["tenant_id"],
        kwargs["ci_type"],
        kwargs["ci_subtype"],
        kwargs["ci_code"],
        kwargs["ci_name"],
        kwargs["ci_category"],
        kwargs["status"],
        kwargs["criticality"],
        kwargs["location"],
        kwargs["owner"],
        created,
        updated,
        kwargs.get("deleted_at"),
    )


def build_ext_row(ci_id: uuid.UUID, attributes: dict, tags: dict) -> tuple:
    return (str(ci_id), json.dumps(attributes), json.dumps(tags))


def main() -> None:
    ci_rows: list[tuple] = []
    ext_rows: list[tuple] = []

    for system in SYSTEM_DEFINITIONS:
        system_id = uuid.uuid4()
        ci_rows.append(
            build_ci_row(
                system_id,
                tenant_id="t1",
                ci_type="SYSTEM",
                ci_subtype=system["subtype"],
                ci_code=f"sys-{system['code']}",
                ci_name=f"{system['name']} System",
                ci_category=system["category"],
                status="active",
                criticality=5,
                location=random.choice(ZONE_OPTIONS),
                owner=system["owner"],
            )
        )
        ext_rows.append(
            build_ext_row(
                system_id,
                {
                    "purpose": system["category"],
                    "depends_on": system["depends_on"],
                },
                {"system": system["code"], "role": "system"},
            )
        )

        server_count = random.randint(4, 6)
        server_codes: list[str] = []
        for server_idx in range(1, server_count + 1):
            server_code = f"srv-{system['code']}-{server_idx:02d}"
            server_id = uuid.uuid4()
            server_codes.append(server_code)
            zone = random.choice(ZONE_OPTIONS)
            ci_rows.append(
                build_ci_row(
                    server_id,
                    tenant_id="t1",
                    ci_type="HW",
                    ci_subtype="server",
                    ci_code=server_code,
                    ci_name=f"{system['name']} Server {server_idx:02d}",
                    ci_category=CI_CATEGORY_MAP["HW"],
                    status=random.choice(["active", "monitoring"]),
                    criticality=4,
                    location=zone,
                    owner=f"{system['code']}-platform",
                )
            )
            ext_rows.append(
                build_ext_row(
                    server_id,
                    {
                        "cpu_cores": random.choice([16, 24, 32]),
                        "memory_gb": random.choice([128, 192, 256]),
                        "ip": f"10.{random.randint(0, 240)}.{server_idx}.{random.randint(2, 254)}",
                        "zone": zone,
                    },
                    {"system": system["code"], "role": "server"},
                )
            )

            os_id = uuid.uuid4()
            os_code = f"os-{system['code']}-{server_idx:02d}"
            ci_rows.append(
                build_ci_row(
                    os_id,
                    tenant_id="t1",
                    ci_type="SW",
                    ci_subtype="os",
                    ci_code=os_code,
                    ci_name=f"{system['name']} OS {server_idx:02d}",
                    ci_category=CI_CATEGORY_MAP["SW"],
                    status="active",
                    criticality=4,
                    location=zone,
                    owner=f"{system['code']}-platform",
                )
            )
            ext_rows.append(
                build_ext_row(
                    os_id,
                    {
                        "engine": "Linux",
                        "version": random.choice(["8.4", "9.1", "9.3"]),
                        "host_server": server_code,
                    },
                    {"system": system["code"], "host_server": server_code},
                )
            )

            db_entry = _maybe_create_db(system, server_code, server_idx)
            if db_entry:
                ci_rows.append(db_entry[0])
                ext_rows.append(db_entry[1])

            was_entry = _build_was(system, server_code, server_idx)
            ci_rows.append(was_entry[0])
            ext_rows.append(was_entry[1])

            web_entry = _maybe_create_web(system, server_code, server_idx, was_entry[2])
            if web_entry:
                ci_rows.append(web_entry[0])
                ext_rows.append(web_entry[1])

            app_entries = _build_apps(system, server_code, server_idx, was_entry[2])
            for app_row, app_ext in app_entries:
                ci_rows.append(app_row)
                ext_rows.append(app_ext)

        _build_network_segments(system, server_codes, ci_rows, ext_rows)

    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE metric_value, event_log, maintenance_history, work_history CASCADE"
            )
            cur.execute("TRUNCATE TABLE ci_ext, ci CASCADE")
            ci_insert = """
                INSERT INTO ci (
                    ci_id, tenant_id, ci_type, ci_subtype, ci_code, ci_name,
                    ci_category, status, criticality, location, owner,
                    created_at, updated_at, deleted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(ci_insert, ci_rows)
            ext_insert = """
                INSERT INTO ci_ext (ci_id, attributes, tags)
                VALUES (%s, %s::jsonb, %s::jsonb)
            """
            cur.executemany(ext_insert, ext_rows)
            conn.commit()

    print(f"Inserted {len(ci_rows)} CI records with {len(ext_rows)} ext rows")


def _maybe_create_db(system: dict[str, Any], server_code: str, server_idx: int) -> tuple | None:
    if random.random() >= 0.4:
        return None
    db_id = uuid.uuid4()
    ci_row = build_ci_row(
        db_id,
        tenant_id="t1",
        ci_type="SW",
        ci_subtype="db",
        ci_code=f"db-{system['code']}-{server_idx:02d}",
        ci_name=f"{system['name']} DB {server_idx:02d}",
        ci_category=CI_CATEGORY_MAP["SW"],
        status="active",
        criticality=3,
        location=random.choice(ZONE_OPTIONS),
        owner=f"{system['code']}-db",
    )
    ext_row = build_ext_row(
        db_id,
        {
            "engine": random.choice(DB_ENGINES),
            "version": "14.0",
            "host_server": server_code,
        },
        {
            "system": system["code"],
            "runs_on": f"os-{system['code']}-{server_idx:02d}",
            "ci_subtype": "db",
            "host_server": server_code,
        },
    )
    return ci_row, ext_row


def _build_was(system: dict[str, Any], server_code: str, server_idx: int) -> tuple[tuple, tuple, str]:
    was_id = uuid.uuid4()
    code = f"was-{system['code']}-{server_idx:02d}"
    ci_row = build_ci_row(
        was_id,
        tenant_id="t1",
        ci_type="SW",
        ci_subtype="was",
        ci_code=code,
        ci_name=f"{system['name']} WAS {server_idx:02d}",
        ci_category=CI_CATEGORY_MAP["SW"],
        status="active",
        criticality=4,
        location=random.choice(ZONE_OPTIONS),
        owner=f"{system['code']}-platform",
    )
    ext_row = build_ext_row(
        was_id,
        {
            "engine": random.choice(WAS_ENGINES),
            "version": "3.2",
            "host_server": server_code,
        },
        {
            "system": system["code"],
            "runs_on": f"os-{system['code']}-{server_idx:02d}",
            "ci_subtype": "was",
            "host_server": server_code,
        },
    )
    return ci_row, ext_row, code


def _maybe_create_web(system: dict[str, Any], server_code: str, server_idx: int, was_code: str) -> tuple | None:
    if random.random() >= 0.5:
        return None
    web_id = uuid.uuid4()
    ci_row = build_ci_row(
        web_id,
        tenant_id="t1",
        ci_type="SW",
        ci_subtype="web",
        ci_code=f"web-{system['code']}-{server_idx:02d}",
        ci_name=f"{system['name']} Web {server_idx:02d}",
        ci_category=CI_CATEGORY_MAP["SW"],
        status="active",
        criticality=3,
        location=random.choice(ZONE_OPTIONS),
        owner=f"{system['code']}-platform",
    )
    ext_row = build_ext_row(
        web_id,
        {
            "engine": random.choice(WEB_ENGINES),
            "version": "1.0",
            "host_server": server_code,
        },
        {
            "system": system["code"],
            "runs_on": was_code,
            "ci_subtype": "web",
            "host_server": server_code,
        },
    )
    return ci_row, ext_row


def _build_apps(system: dict[str, Any], server_code: str, server_idx: int, was_code: str) -> list[tuple[tuple, tuple]]:
    apps: list[tuple[tuple, tuple]] = []
    count = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.1])[0]
    for idx in range(1, count + 1):
        name = random.choice(APP_NAMES)
        app_id = uuid.uuid4()
        ci_code = f"app-{system['code']}-{name}-{server_idx:02d}-{idx}"
        ci_row = build_ci_row(
            app_id,
            tenant_id="t1",
            ci_type="SW",
            ci_subtype="app",
            ci_code=ci_code,
            ci_name=f"{system['name']} App {name.title()} {server_idx:02d}-{idx}",
            ci_category=CI_CATEGORY_MAP["SW"],
            status="active",
            criticality=3,
            location=random.choice(ZONE_OPTIONS),
            owner=f"{system['code']}-apps",
        )
        ext_row = build_ext_row(
            app_id,
            {
                "language": random.choice(APP_LANGUAGES),
                "repo": f"https://git.internal/{system['code']}/{name}-{server_idx:02d}",
                "owner_team": f"{system['code']}-app",
            },
            {
                "system": system["code"],
                "runs_on": was_code,
                "ci_subtype": "app",
                "host_server": server_code,
            },
        )
        apps.append((ci_row, ext_row))
    return apps


def _build_network_segments(
    system: dict[str, Any], server_codes: list[str], ci_rows: list[tuple], ext_rows: list[tuple]
) -> None:
    for idx in range(1, 3):
        net_id = uuid.uuid4()
        code = f"net-{system['code']}-{idx:02d}"
        ci_rows.append(
            build_ci_row(
                net_id,
                tenant_id="t1",
                ci_type="HW",
                ci_subtype="network",
                ci_code=code,
                ci_name=f"{system['name']} Network {idx:02d}",
                ci_category=CI_CATEGORY_MAP["HW"],
                status="active",
                criticality=3,
                location=random.choice(ZONE_OPTIONS),
                owner=f"{system['code']}-network",
            )
        )
        ext_rows.append(
            build_ext_row(
                net_id,
                {
                    "vendor": random.choice(NETWORK_VENDORS),
                    "ports": random.choice([24, 48, 64]),
                    "connected_servers": server_codes,
                },
                {"system": system["code"], "ci_subtype": "network"},
            )
        )
    storage_id = uuid.uuid4()
    ci_rows.append(
        build_ci_row(
            storage_id,
            tenant_id="t1",
            ci_type="HW",
            ci_subtype="storage",
            ci_code=f"storage-{system['code']}",
            ci_name=f"{system['name']} Storage",
            ci_category=CI_CATEGORY_MAP["HW"],
            status="active",
            criticality=3,
            location=random.choice(ZONE_OPTIONS),
            owner=f"{system['code']}-storage",
        )
    )
    ext_rows.append(
        build_ext_row(
            storage_id,
            {
                "capacity_tb": random.choice([10, 20, 40]),
                "raid": random.choice(STORAGE_RAIDS),
            },
            {"system": system["code"], "ci_subtype": "storage"},
        )
    )
    security_id = uuid.uuid4()
    ci_rows.append(
        build_ci_row(
            security_id,
            tenant_id="t1",
            ci_type="HW",
            ci_subtype="security",
            ci_code=f"sec-{system['code']}",
            ci_name=f"{system['name']} Security",
            ci_category=CI_CATEGORY_MAP["HW"],
            status="active",
            criticality=4,
            location=random.choice(ZONE_OPTIONS),
            owner=f"{system['code']}-security",
        )
    )
    ext_rows.append(
        build_ext_row(
            security_id,
            {"fw_version": f"fw-{random.randint(100, 999)}"},
            {"system": system["code"], "ci_subtype": "security"},
        )
    )


if __name__ == "__main__":
    main()
