from main import app


def test_documents_routes_use_document_processor_router_only():
    legacy_routes = []
    for route in app.routes:
        path = getattr(route, "path", "")
        endpoint = getattr(route, "endpoint", None)
        module_name = getattr(endpoint, "__module__", "")
        if path.startswith("/api/documents") and module_name.startswith("api.routes.documents"):
            legacy_routes.append((path, module_name))

    assert legacy_routes == []
