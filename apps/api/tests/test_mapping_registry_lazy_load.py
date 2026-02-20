from app.modules.ops.services.orchestration.mappings.registry import MappingRegistry


def test_get_mapping_lazy_loads_from_asset_registry(monkeypatch):
    registry = MappingRegistry()
    payload = {"metric_aliases": {"aliases": {"cpu": "cpu_usage"}}}

    def fake_load_mapping_asset(mapping_name: str, version=None, scope=None):
        assert mapping_name == "planner_keywords"
        return payload, "asset_registry:planner_keywords:v1"

    monkeypatch.setattr(
        "app.modules.asset_registry.loader.load_mapping_asset",
        fake_load_mapping_asset,
    )

    loaded = registry.get_mapping("planner_keywords")

    assert loaded == payload
    assert registry.is_registered("planner_keywords")
    assert registry.get_mapping_info("planner_keywords")["source"] == "asset_registry(lazy)"


def test_get_mapping_raises_when_asset_missing(monkeypatch):
    registry = MappingRegistry()

    monkeypatch.setattr(
        "app.modules.asset_registry.loader.load_mapping_asset",
        lambda *_args, **_kwargs: (None, None),
    )

    try:
        registry.get_mapping("planner_keywords")
        assert False, "Expected KeyError when mapping asset is missing"
    except KeyError as exc:
        assert "planner_keywords" in str(exc)
