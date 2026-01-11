from datetime import datetime, timedelta, timezone

import pytest

from core.config import AppSettings
from core.db_neo4j import get_neo4j_driver
from schemas import MarkdownBlock, ReferenceItem, ReferencesBlock
from app.modules.ops.services import handle_ops_query
from app.modules.ops.services.resolvers.types import CIHit, TimeRange


@pytest.fixture(autouse=True)
def clear_settings() -> None:
    AppSettings.connection_cache.clear()
    yield
    AppSettings.connection_cache.clear()


def test_handle_ops_query_mock_mode_uses_mock_blocks(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "mock")
    envelope = handle_ops_query("metric", "What is cpu health?")
    assert envelope.meta.route == "metric"
    assert envelope.meta.used_tools == ["mock"]
    assert not envelope.meta.fallback
    assert envelope.blocks
    assert any(block.type == "timeseries" for block in envelope.blocks if hasattr(block, "type"))


def test_handle_ops_query_real_mode_fallbacks_and_flags_error(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    envelope = handle_ops_query("metric", "What is cpu health?")
    assert envelope.meta.route == "metric"
    assert envelope.meta.fallback
    assert envelope.meta.error
    assert "CI not found" in envelope.meta.error
    assert envelope.meta.used_tools == ["mock"]


def _has_postgres() -> bool:
    from scripts.seed.utils import get_postgres_conn

    try:
        with get_postgres_conn():
            return True
    except Exception:
        return False


HAS_DB = _has_postgres()


def _has_neo4j() -> bool:
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            session.run("RETURN 1").single()
        driver.close()
        return True
    except Exception:
        return False


HAS_NEO4J = _has_neo4j()


@pytest.mark.skipif(not HAS_DB, reason="Postgres not configured")
def test_ops_metric_real_blocks_shape(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    envelope = handle_ops_query("metric", "srv-erp-01 CPU 사용률 지난 7일")
    assert any(getattr(block, "type", None) == "markdown" for block in envelope.blocks)
    assert any(getattr(block, "type", None) == "timeseries" for block in envelope.blocks)
    ref_blocks = [block for block in envelope.blocks if getattr(block, "type", None) == "references"]
    assert ref_blocks
    assert any(item.kind == "sql" for block in ref_blocks for item in block.items)
    assert "postgres" in envelope.meta.used_tools
    assert envelope.meta.used_tools.count("timescale") == 1


@pytest.mark.skipif(not HAS_DB, reason="Postgres not configured")
def test_ops_hist_real_blocks_shape(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    envelope = handle_ops_query("hist", "srv-erp-01 최근 이력")
    assert any(getattr(block, "type", None) == "markdown" for block in envelope.blocks)
    assert len([block for block in envelope.blocks if getattr(block, "type", None) == "table"]) >= 1
    ref_blocks = [block for block in envelope.blocks if getattr(block, "type", None) == "references"]
    assert ref_blocks
    assert len([item for block in ref_blocks for item in block.items if item.kind == "sql"]) >= 1
    assert "postgres" in envelope.meta.used_tools and "timescale" in envelope.meta.used_tools


@pytest.mark.skipif(not (HAS_DB and HAS_NEO4J), reason="Postgres or Neo4j not configured")
def test_ops_graph_real_blocks_shape(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    envelope = handle_ops_query("graph", "srv-erp-01 영향도 보여줘")
    assert any(getattr(block, "type", None) == "markdown" for block in envelope.blocks)
    graph_blocks = [block for block in envelope.blocks if getattr(block, "type", None) == "graph"]
    assert graph_blocks
    assert graph_blocks[0].nodes
    ref_blocks = [block for block in envelope.blocks if getattr(block, "type", None) == "references"]
    assert ref_blocks
    assert any(item.kind == "cypher" for block in ref_blocks for item in block.items)
    assert "neo4j" in envelope.meta.used_tools and "postgres" in envelope.meta.used_tools


@pytest.mark.skipif(
    not (HAS_DB and HAS_NEO4J),
    reason="Postgres or Neo4j not configured",
)
def test_ops_all_real_blocks_shape(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    envelope = handle_ops_query("all", "srv-erp-01 CPU 사용률 지난 7일 영향도")
    assert envelope.meta.route == "all"
    assert not envelope.meta.fallback
    assert envelope.blocks
    assert envelope.blocks[0].title == "ALL summary"
    assert any(getattr(block, "type", None) == "graph" for block in envelope.blocks)
    assert "postgres" in envelope.meta.used_tools and "neo4j" in envelope.meta.used_tools


@pytest.mark.skipif(
    not (HAS_DB and HAS_NEO4J),
    reason="Postgres or Neo4j not configured",
)
def test_ops_all_langgraph_without_key_falls_back(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    monkeypatch.setenv("OPS_ENABLE_LANGGRAPH", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    envelope = handle_ops_query("all", "srv-erp-01 CPU 사용률 지난 7일 영향도")
    assert envelope.meta.route == "all"
    assert envelope.blocks[0].title == "ALL summary"
    assert not envelope.meta.fallback


def test_ops_all_partial_failure(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")

    now = datetime.now(timezone.utc)
    fake_ci = CIHit(
        ci_id="stub-id",
        ci_code="srv-erp-01",
        ci_name="ERP Server 01",
        ci_type="HW",
        ci_subtype="server",
        ci_category="business",
        score=1.0,
    )
    fake_range = TimeRange(start=now - timedelta(hours=1), end=now, bucket="5 minutes")

    def fake_metric(_question: str):
        return (
            [
                MarkdownBlock(type="markdown", title="Metric stub", content="stub"),
                ReferencesBlock(
                    type="references",
                    title="metric stub ref",
                    items=[
                        ReferenceItem(
                            kind="sql",
                            title="stub query",
                            payload={"sql": "SELECT 1", "params": []},
                        )
                    ],
                ),
            ],
            ["timescale"],
        )

    def failing_hist(_question: str):
        raise RuntimeError("hist service unavailable")

    def stub_ci(_question: str):
        return [fake_ci]

    def stub_time_range(_question: str, _now: datetime, tz=None):
        return fake_range

    monkeypatch.setattr("app.modules.ops.services.run_metric", fake_metric)
    monkeypatch.setattr("app.modules.ops.services.run_hist", failing_hist)
    monkeypatch.setattr("app.modules.ops.services.resolve_ci", stub_ci)
    monkeypatch.setattr("app.modules.ops.services.resolve_time_range", stub_time_range)

    envelope = handle_ops_query("all", "stub question")
    assert envelope.meta.route == "all"
    assert not envelope.meta.fallback
    assert envelope.meta.error and "hist service unavailable" in envelope.meta.error
    assert "timescale" in envelope.meta.used_tools
    assert envelope.blocks[0].title == "ALL summary"
    assert any(block.title == "Metric stub" for block in envelope.blocks if getattr(block, "type", None) == "markdown")


def test_ops_config_placeholder(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "mock")
    envelope = handle_ops_query("config", "전체 구성 상태 확인")
    assert envelope.meta.route == "config"
    assert not envelope.meta.fallback
    assert envelope.meta.used_tools == ["placeholder"]
    assert envelope.blocks
    assert any(getattr(block, "type", None) == "markdown" for block in envelope.blocks)
    assert any(getattr(block, "type", None) == "table" for block in envelope.blocks)
    assert any(getattr(block, "type", None) == "references" for block in envelope.blocks)


@pytest.mark.skipif(not HAS_DB, reason="Postgres not configured")
def test_ops_config_real_blocks_shape(monkeypatch):
    monkeypatch.setenv("OPS_MODE", "real")
    envelope = handle_ops_query("config", "srv-erp-01 구성 정보")
    assert envelope.meta.route == "config"
    assert not envelope.meta.fallback
    assert any(getattr(block, "type", None) == "markdown" for block in envelope.blocks)
    assert len([block for block in envelope.blocks if getattr(block, "type", None) == "table"]) >= 2
    ref_blocks = [block for block in envelope.blocks if getattr(block, "type", None) == "references"]
    assert ref_blocks
    assert any(item.kind == "sql" for block in ref_blocks for item in block.items)
    assert "postgres" in envelope.meta.used_tools
