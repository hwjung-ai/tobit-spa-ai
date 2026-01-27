from __future__ import annotations

import json
from typing import Any

import psycopg
from schemas import (
    AnswerBlock,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TableBlock,
)

from app.modules.asset_registry.loader import load_query_asset, load_source_asset
from app.modules.ops.services.connections import ConnectionFactory
from app.shared.config_loader import load_text
from core.config import get_settings

from ..resolvers import resolve_ci
from ..resolvers.types import CIHit


def _get_connection():
    """Get connection for config operations using source asset."""
    settings = get_settings()
    source_asset = load_source_asset(settings.ops_default_source_asset)
    return ConnectionFactory.create(source_asset)


def _load_query_sql(scope: str, name: str) -> str | None:
    """Load query SQL with DB priority fallback to file."""
    asset, _ = load_query_asset(scope, name)
    if asset:
        return asset.get("sql")
    return None


def run_config(
    question: str, tenant_id: str = "t1"
) -> tuple[list[AnswerBlock], list[str]]:
    # Load queries with DB priority fallback to files
    ci_select_query = _load_query_sql("ci", "resolve_ci") or load_text(
        "queries/postgres/ci/resolve_ci.sql"
    )
    ci_ext_select_query = _load_query_sql("ci", "ci_attributes") or load_text(
        "queries/postgres/ci/ci_attributes.sql"
    )

    if not ci_select_query or not ci_ext_select_query:
        return [
            MarkdownBlock(
                type="markdown",
                title="Error",
                content="### 쿼리 파일 로드 실패\n- `resolve_ci.sql` 또는 `ci_attributes.sql` 파일을 찾을 수 없거나 읽는 데 실패했습니다.",
            )
        ], []

    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        # Per user request, do not fallback to mock. Return markdown guide.
        return [
            MarkdownBlock(
                type="markdown",
                title="CI 조회 결과",
                content="질문에서 CI를 찾을 수 없습니다. `MES_App_Report_02-2의 상태`와 같이 명확한 CI를 지정하여 질문해주세요.",
            )
        ], []
    ci = ci_hits[0]

    try:
        connection = _get_connection()
        try:
            conn = connection.connection if hasattr(connection, 'connection') else connection
            ci_row = _fetch_ci(conn, ci_select_query, tenant_id, ci.ci_id)
            if not ci_row:
                return [
                    MarkdownBlock(
                        type="markdown",
                        title="CI 조회 결과",
                        content=f"CI '{ci.ci_code}'에 대한 레코드를 찾을 수 없습니다.",
                    )
                ], ["postgres"]
            ci_ext = _fetch_ci_ext(conn, ci_ext_select_query, ci.ci_id)
        finally:
            connection.close()
    except Exception as e:
        return [
            MarkdownBlock(
                type="markdown",
                title="Database Error",
                content=f"데이터베이스 조회 중 오류가 발생했습니다:\n```\n{str(e)}\n```",
            )
        ], []

    blocks = _build_blocks(
        ci, ci_row, ci_ext, tenant_id, ci_select_query, ci_ext_select_query
    )
    return blocks, ["postgres"]


def _fetch_ci(conn, query: str, tenant_id: str, ci_id: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(query, (tenant_id, ci_id))
        return cur.fetchone()


def _fetch_ci_ext(conn, query: str, ci_id: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(query, (ci_id,))
        return cur.fetchone()


def _normalize_json_blob(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"value": value}
    if isinstance(value, dict):
        return value
    return {"value": value}


def _build_blocks(
    ci: CIHit,
    ci_row: dict[str, Any],
    ci_ext: dict[str, Any] | None,
    tenant_id: str,
    ci_select_query: str,
    ci_ext_select_query: str,
) -> list[AnswerBlock]:
    markdown = MarkdownBlock(
        type="markdown",
        title="CI 구성 조회 결과",
        content=(
            f"CI: {ci_row['ci_code']} ({ci_row['ci_name']})\n"
            f"Type: {ci_row['ci_type']} / {ci_row['ci_subtype']}\n"
            f"Status: {ci_row['status']} / Criticality: {ci_row['criticality']}"
        ),
    )
    base_rows = [
        ["ci_code", ci_row["ci_code"]],
        ["ci_name", ci_row["ci_name"]],
        ["ci_type", ci_row["ci_type"]],
        ["ci_subtype", ci_row["ci_subtype"]],
        ["status", ci_row["status"]],
        ["criticality", str(ci_row["criticality"])],
        ["owner", ci_row["owner"]],
        ["location", ci_row["location"]],
        [
            "updated_at",
            ci_row["updated_at"].isoformat() if ci_row["updated_at"] else "unknown",
        ],
    ]
    base_table = TableBlock(
        type="table",
        title="CI core attributes",
        columns=["field", "value"],
        rows=base_rows,
    )
    attr_rows: list[list[str]] = []
    tag_rows: list[list[str]] = []
    if ci_ext:
        attributes = _normalize_json_blob(ci_ext.get("attributes"))
        for key, value in attributes.items():
            attr_rows.append([key, json.dumps(value, ensure_ascii=False)])
        tags = ci_ext.get("tags")
        if tags is None:
            tag_rows.append(["tags", "none"])
        elif isinstance(tags, dict):
            for key, value in tags.items():
                tag_rows.append([key, json.dumps(value, ensure_ascii=False)])
        elif isinstance(tags, list):
            for idx, value in enumerate(tags, 1):
                tag_rows.append([f"tag[{idx}]", json.dumps(value, ensure_ascii=False)])
        else:
            tag_rows.append(["tags", json.dumps(tags, ensure_ascii=False)])
    attributes_table = TableBlock(
        type="table",
        title="CI extended attributes",
        columns=["field", "value"],
        rows=attr_rows or [["attributes", "none"]],
    )
    tags_table = TableBlock(
        type="table",
        title="CI tags",
        columns=["field", "value"],
        rows=tag_rows or [["tags", "none"]],
    )
    references = ReferencesBlock(
        type="references",
        title="Config SQL",
        items=[
            ReferenceItem(
                kind="sql",
                title="ci lookup",
                payload={
                    "sql": ci_select_query.strip(),
                    "params": [tenant_id, ci.ci_id],
                },
            ),
            ReferenceItem(
                kind="sql",
                title="ci_ext lookup",
                payload={"sql": ci_ext_select_query.strip(), "params": [ci.ci_id]},
            ),
        ],
    )
    return [markdown, base_table, attributes_table, tags_table, references]
