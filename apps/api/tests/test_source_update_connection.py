from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.modules.asset_registry.crud import update_source_asset
from app.modules.asset_registry.source_models import (
    SourceAssetUpdate,
    SourceConnection,
)


def test_update_source_asset_persists_connection_username(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_db_asset = SimpleNamespace(
        asset_id="11111111-1111-4111-8111-111111111111",
        asset_type="source",
        status="draft",
        content={
            "source_type": "postgresql",
            "connection": {
                "host": "localhost",
                "port": 5432,
                "username": "old_user",
                "database": "spadb",
                "timeout": 30,
            },
        },
        updated_at=datetime.now(),
    )

    def _fake_get_asset(session, asset_id):  # noqa: ANN001
        return fake_db_asset

    def _fake_update_asset(session, asset, updates, updated_by=None):  # noqa: ANN001
        captured["asset"] = asset
        captured["updates"] = updates
        captured["updated_by"] = updated_by
        asset.content = updates.get("content", asset.content)

    def _fake_get_source_asset(session, asset_id):  # noqa: ANN001
        return SimpleNamespace(asset_id=asset_id, connection=SourceConnection(username="new_user"))

    monkeypatch.setattr("app.modules.asset_registry.crud.get_asset", _fake_get_asset)
    monkeypatch.setattr("app.modules.asset_registry.crud.update_asset", _fake_update_asset)
    monkeypatch.setattr("app.modules.asset_registry.crud.get_source_asset", _fake_get_source_asset)

    updates = SourceAssetUpdate(
        connection=SourceConnection(
            host="localhost",
            port=5432,
            username="new_user",
            database="spadb",
            timeout=30,
        )
    )

    result = update_source_asset(
        session=SimpleNamespace(),
        asset_id="11111111-1111-4111-8111-111111111111",
        updates=updates,
        updated_by="tester",
    )

    assert result.asset_id == "11111111-1111-4111-8111-111111111111"
    assert captured["asset"] is fake_db_asset
    assert captured["updated_by"] == "tester"
    content = captured["updates"]["content"]  # type: ignore[index]
    assert content["connection"]["username"] == "new_user"  # type: ignore[index]


def test_update_source_asset_allows_published_source_update(monkeypatch) -> None:
    fake_db_asset = SimpleNamespace(
        asset_id="22222222-2222-4222-8222-222222222222",
        asset_type="source",
        status="published",
        name="published_source",
        content={
            "source_type": "postgresql",
            "connection": {
                "host": "localhost",
                "port": 5432,
                "username": "old_user",
                "database": "spadb",
                "timeout": 30,
            },
        },
        updated_at=datetime.now(),
    )

    captured: dict[str, object] = {"committed": False}

    def _fake_get_asset(session, asset_id):  # noqa: ANN001
        return fake_db_asset

    def _fake_get_source_asset(session, asset_id):  # noqa: ANN001
        return SimpleNamespace(asset_id=asset_id, connection=SourceConnection(username="new_user"))

    def _forbidden_update_asset(*args, **kwargs):  # noqa: ANN001, ANN002, ARG001
        raise AssertionError("update_asset must not be called for published source updates")

    class _FakeSession:
        def add(self, asset):  # noqa: ANN001
            if hasattr(asset, "asset_type"):
                captured["asset"] = asset

        def commit(self) -> None:
            captured["committed"] = True

        def refresh(self, asset) -> None:  # noqa: ANN001
            return None

    monkeypatch.setattr("app.modules.asset_registry.crud.get_asset", _fake_get_asset)
    monkeypatch.setattr("app.modules.asset_registry.crud.get_source_asset", _fake_get_source_asset)
    monkeypatch.setattr("app.modules.asset_registry.crud.update_asset", _forbidden_update_asset)

    updates = SourceAssetUpdate(
        connection=SourceConnection(
            host="localhost",
            port=5432,
            username="new_user",
            database="spadb",
            timeout=30,
        )
    )

    result = update_source_asset(
        session=_FakeSession(),
        asset_id="22222222-2222-4222-8222-222222222222",
        updates=updates,
        updated_by="tester",
    )

    assert result.asset_id == "22222222-2222-4222-8222-222222222222"
    assert captured["asset"] is fake_db_asset
    assert captured["committed"] is True
    assert fake_db_asset.content["connection"]["username"] == "new_user"
