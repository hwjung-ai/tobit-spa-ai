"""Configuration for OPS E2E tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))



class E2EArtifactCollector:
    """Collector for E2E test artifacts."""

    def __init__(self, root: Path):
        self.root = root
        self.raw_dir = self.root / "e2e_raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_entry(self, entry: Dict[str, Any]) -> None:
        self.entries.append(entry)

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value


@pytest.fixture(scope="session")
def e2e_artifact_collector(request) -> E2EArtifactCollector:
    """Artifact collector for E2E tests."""
    collector = E2EArtifactCollector(Path("artifacts"))
    request.config.ops_e2e_artifacts = collector

    # Set metadata
    collector.set_metadata("base_url", os.environ.get("OPS_BASE_URL", "http://localhost:8000"))
    collector.set_metadata("assume_real_mode", os.environ.get("OPS_ASSUME_REAL_MODE", "true"))
    collector.set_metadata("test_environment", os.environ.get("TEST_ENV", "development"))

    return collector


@pytest.fixture(scope="session")
def e2e_client() -> httpx.Client:
    """HTTP client for E2E tests."""
    base_url = os.environ.get("OPS_BASE_URL", "http://localhost:8000")

    with httpx.Client(base_url=base_url, timeout=60) as client:
        # Wait for service to be ready
        try:
            response = client.get("/health")
            response.raise_for_status()
        except httpx.HTTPError:
            pytest.skip("OPS service not available")

        yield client


def pytest_sessionfinish(session, exitstatus):
    """Generate summary report after session finish."""
    collector: E2EArtifactCollector | None = getattr(session.config, "ops_e2e_artifacts", None)
    if not collector:
        return

    # Generate summary
    summary_path = collector.root / "ops_e2e_summary.json"
    payload = {
        "metadata": collector.metadata,
        "total_tests": len(collector.entries),
        "passed": len([e for e in collector.entries if e.get("status") == "pass"]),
        "failed": len([e for e in collector.entries if e.get("status") == "fail"]),
        "skipped": len([e for e in collector.entries if e.get("status") == "skipped"]),
        "entries": collector.entries
    }

    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))