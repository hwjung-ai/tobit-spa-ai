from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.inspector.models import TbExecutionTrace
from core.db import get_session
from fastapi.testclient import TestClient
from main import app
from sqlmodel import Session


def _make_client(session: Session) -> TestClient:
    def override_get_session():
        return session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_list_asset_traces_returns_traces(session: Session) -> None:
    asset = TbAssetRegistry(
        asset_type="source",
        name="Source Asset",
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)

    trace = TbExecutionTrace(
        trace_id="trace-asset-001",
        feature="ci",
        endpoint="/ops/ask",
        method="POST",
        ops_mode="real",
        question="What is the impact?",
        status="success",
        duration_ms=120,
        asset_versions=[str(asset.asset_id)],
    )
    session.add(trace)
    session.commit()

    client = _make_client(session)
    response = client.get(f"/asset-registry/assets/{asset.asset_id}/traces?limit=10")

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert data["total"] == 1
    assert data["traces"][0]["trace_id"] == "trace-asset-001"
    assert str(asset.asset_id) in data["traces"][0]["applied_asset_versions"]
