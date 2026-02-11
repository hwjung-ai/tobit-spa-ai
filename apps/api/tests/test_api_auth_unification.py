from __future__ import annotations

from main import app


PUBLIC_PATHS = {
    "/auth/login",
    "/auth/refresh",
}


def _collect_dependency_names(dependant, names: set[str]) -> None:
    if dependant is None:
        return
    call = getattr(dependant, "call", None)
    if call is not None:
        names.add(getattr(call, "__name__", str(call)))
    for child in getattr(dependant, "dependencies", []) or []:
        _collect_dependency_names(child, names)


def test_all_api_routes_require_auth_except_public_endpoints() -> None:
    unsecured: list[str] = []

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        dependant = getattr(route, "dependant", None)
        if not path or not methods or dependant is None:
            continue

        # Skip non-API utility endpoints when enabled.
        if path in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
            continue

        names: set[str] = set()
        _collect_dependency_names(dependant, names)

        if path in PUBLIC_PATHS:
            continue

        if "get_current_user" not in names:
            method_list = ",".join(
                sorted(m for m in methods if m not in {"HEAD", "OPTIONS"})
            )
            unsecured.append(f"{method_list} {path}")

    assert not unsecured, "Unsecured API routes found:\n" + "\n".join(sorted(unsecured))
