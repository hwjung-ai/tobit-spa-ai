from __future__ import annotations

from main import app


def _first_route_module(path: str, method: str) -> str | None:
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if method.upper() not in methods:
            continue
        return route.endpoint.__module__
    return None


def test_tool_test_endpoint_prefers_dedicated_tool_router() -> None:
    module_name = _first_route_module("/asset-registry/tools/{asset_id}/test", "POST")
    assert module_name == "app.modules.asset_registry.tool_router"


def test_tool_publish_endpoint_prefers_dedicated_tool_router() -> None:
    module_name = _first_route_module("/asset-registry/tools/{asset_id}/publish", "POST")
    assert module_name == "app.modules.asset_registry.tool_router"


def test_tool_unpublish_endpoint_prefers_dedicated_tool_router() -> None:
    module_name = _first_route_module("/asset-registry/tools/{asset_id}/unpublish", "POST")
    assert module_name == "app.modules.asset_registry.tool_router"
