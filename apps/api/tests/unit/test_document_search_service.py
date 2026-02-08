from __future__ import annotations

from app.modules.document_processor.services.search_service import DocumentSearchService


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.last_sql = None
        self.last_params = None

    def execute(self, statement, params):
        self.last_sql = str(statement)
        self.last_params = params
        return _FakeResult(self.rows)


def test_get_search_suggestions_returns_empty_without_db():
    svc = DocumentSearchService(db_session=None)
    assert svc.get_search_suggestions("disk", limit=5, tenant_id="t1") == []


def test_get_search_suggestions_queries_db_with_tenant():
    fake = _FakeSession(rows=[("disk latency", 10), ("disk io", 4)])
    svc = DocumentSearchService(db_session=fake)

    suggestions = svc.get_search_suggestions("disk", limit=5, tenant_id="t1")

    assert suggestions == ["disk latency", "disk io"]
    assert fake.last_params["tenant_id"] == "t1"
    assert fake.last_params["prefix"] == "disk%"
