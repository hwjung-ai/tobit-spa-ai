from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# These files may contain tenant header placeholders in outbound tool templates.
ALLOWLIST = {
    "app/modules/asset_registry/tool_router.py",
    "tools/init_document_search_tool.py",
}

FORBIDDEN_SNIPPETS = (
    'request.headers.get("X-User-Id"',
    'request.headers.get("X-Tenant-Id"',
    'Header(None, alias="X-User-Id")',
    'Header(None, alias="X-Tenant-Id")',
)


def test_no_direct_identity_headers_in_runtime_sources() -> None:
    violations: list[str] = []
    for py_file in ROOT.rglob("*.py"):
        rel = py_file.relative_to(ROOT).as_posix()
        if rel.startswith("tests/") or rel.startswith("scripts/"):
            continue
        if rel in ALLOWLIST:
            continue
        content = py_file.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in content:
                violations.append(f"{rel}: contains `{snippet}`")
    assert not violations, "Forbidden direct identity header access found:\n" + "\n".join(
        violations
    )
