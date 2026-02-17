from __future__ import annotations

from app.modules.ops.services.connections.sql_processor import SQLTemplateProcessor


def test_escape_literal_percents_keeps_placeholders() -> None:
    sql = "SELECT * FROM t WHERE a=%s AND b LIKE '%cpu%'"
    escaped = SQLTemplateProcessor.escape_literal_percents(sql)
    assert escaped == "SELECT * FROM t WHERE a=%s AND b LIKE '%%cpu%%'"


def test_escape_literal_percents_keeps_named_placeholders() -> None:
    sql = "SELECT * FROM t WHERE tenant_id=%(tenant_id)s AND name LIKE '%ops%'"
    escaped = SQLTemplateProcessor.escape_literal_percents(sql)
    assert (
        escaped
        == "SELECT * FROM t WHERE tenant_id=%(tenant_id)s AND name LIKE '%%ops%%'"
    )
