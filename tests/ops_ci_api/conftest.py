from __future__ import annotations

import json  # noqa: E402
import os  # noqa: E402
import random  # noqa: E402
import sys
from dataclasses import dataclass  # noqa: E402
from pathlib import Path
from typing import Any, Dict  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.scripts.seed import seed_ci  # noqa: E402


class ArtifactCollector:
    def __init__(self, root: Path):
        self.root = root
        self.raw_dir = self.root / "ops_ci_api_raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_entry(self, entry: Dict[str, Any]) -> None:
        self.entries.append(entry)

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value


class SeedCodeSampler:
    def __init__(self) -> None:
        self.rnd = random.Random(0)

    def collect(self) -> Dict[str, list[str]]:
        servers: list[str] = []
        oses: list[str] = []
        apps: list[str] = []
        for system in seed_ci.SYSTEM_DEFINITIONS:
            self.rnd.choice(seed_ci.ZONE_OPTIONS)  # system location allocation
            server_count = self.rnd.randint(4, 6)
            for server_idx in range(1, server_count + 1):
                self.rnd.choice(seed_ci.ZONE_OPTIONS)
                self.rnd.choice(["active", "monitoring"])
                server_code = f"srv-{system['code']}-{server_idx:02d}"
                servers.append(server_code)
                os_code = f"os-{system['code']}-{server_idx:02d}"
                oses.append(os_code)
                self.rnd.choice(["8.4", "9.1", "9.3"])
                if self.rnd.random() < 0.4:
                    self.rnd.choice(seed_ci.DB_ENGINES)
                self.rnd.choice(seed_ci.ZONE_OPTIONS)
                self.rnd.choice(seed_ci.WAS_ENGINES)
                if self.rnd.random() < 0.5:
                    self.rnd.choice(seed_ci.WEB_ENGINES)
                count = self.rnd.choices([1, 2, 3], weights=[0.65, 0.25, 0.1])[0]
                for idx in range(1, count + 1):
                    name = self.rnd.choice(seed_ci.APP_NAMES)
                    app_code = f"app-{system['code']}-{name}-{server_idx:02d}-{idx}"
                    apps.append(app_code)
                    self.rnd.choice(seed_ci.APP_LANGUAGES)
            self._consume_network_randoms()
        return {"servers": servers, "oses": oses, "apps": apps}

    def _consume_network_randoms(self) -> None:
        for _ in range(2):
            self.rnd.choice(seed_ci.ZONE_OPTIONS)
            self.rnd.choice(seed_ci.NETWORK_VENDORS)
            self.rnd.choice([24, 48, 64])
        self.rnd.choice(seed_ci.ZONE_OPTIONS)
        self.rnd.choice([10, 20, 40])
        self.rnd.choice(seed_ci.STORAGE_RAIDS)
        self.rnd.choice(seed_ci.ZONE_OPTIONS)
        self.rnd.randint(100, 999)


@dataclass
class SampleCodes:
    server: str
    os: str
    app: str


def _fetch_codes_from_db(dsn: str) -> dict[str, str] | None:
    try:
        import psycopg
    except ImportError:
        return None
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ci_code FROM ci WHERE ci_code LIKE 'srv-%' ORDER BY ci_code LIMIT 1")
                server = cur.fetchone()
                cur.execute("SELECT ci_code FROM ci WHERE ci_code LIKE 'os-%' ORDER BY ci_code LIMIT 1")
                os_code = cur.fetchone()
                cur.execute("SELECT ci_code FROM ci WHERE ci_code LIKE 'app-%' ORDER BY ci_code LIMIT 1")
                app = cur.fetchone()
    except Exception:
        return None
    if server and os_code and app:
        return {"server": server[0], "os": os_code[0], "app": app[0]}
    return None


@pytest.fixture(scope="session")
def artifact_collector(request) -> ArtifactCollector:
    collector = ArtifactCollector(Path("artifacts"))
    request.config.ops_ci_artifacts = collector
    collector.set_metadata("ops_assume_real_mode", os.environ.get("OPS_ASSUME_REAL_MODE", "true"))
    collector.set_metadata("base_url", os.environ.get("OPS_BASE_URL", "http://localhost:8000"))
    collector.set_metadata("ci_endpoint", os.environ.get("OPS_CI_ENDPOINT", "/ops/ask"))
    collector.set_metadata("seed_range", {
        "from": os.environ.get("OPS_SEED_FROM", "2025-12-01"),
        "to": os.environ.get("OPS_SEED_TO", "2025-12-31"),
    })
    return collector


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("OPS_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def ci_endpoint() -> str:
    return os.environ.get("OPS_CI_ENDPOINT", "/ops/ask")


@pytest.fixture(scope="session")
def time_range() -> tuple[str, str]:
    return (
        os.environ.get("OPS_SEED_FROM", "2025-12-01"),
        os.environ.get("OPS_SEED_TO", "2025-12-31"),
    )


@pytest.fixture(scope="session")
def sample_codes(artifact_collector: ArtifactCollector) -> SampleCodes:
    strategy = "seed"
    dsn = os.environ.get("OPS_CI_DB_DSN") or os.environ.get("DATABASE_URL")
    codes = None
    if dsn:
        db_codes = _fetch_codes_from_db(dsn)
        if db_codes:
            codes = db_codes
            strategy = "db"
    if not codes:
        sampled = SeedCodeSampler().collect()
        codes = {
            "server": sampled["servers"][0],
            "os": sampled["oses"][0],
            "app": sampled["apps"][0],
        }
    artifact_collector.set_metadata("ci_code_strategy", strategy)
    artifact_collector.set_metadata("ci_codes", codes)
    return SampleCodes(server=codes["server"], os=codes["os"], app=codes["app"])


@pytest.fixture(scope="session")
def http_client(base_url: str) -> httpx.Client:
    with httpx.Client(base_url=base_url, timeout=30) as client:
        yield client


@pytest.fixture(scope="session")
def client(http_client: httpx.Client) -> httpx.Client:
    return http_client


def pytest_sessionfinish(session, exitstatus):
    collector: ArtifactCollector | None = getattr(session.config, "ops_ci_artifacts", None)
    if not collector:
        return
    summary_path = collector.root / "ops_ci_api_summary.json"
    payload = {"metadata": collector.metadata, "entries": collector.entries}
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
