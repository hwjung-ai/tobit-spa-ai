from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from models import ApiDefinition, ApiMode, ApiScope
from schemas import AnswerEnvelope, AnswerMeta, MarkdownBlock, TableBlock


def list_api_definitions(session: Session, scope: ApiScope | None = None) -> list[ApiDefinition]:
    statement = select(ApiDefinition).where(ApiDefinition.deleted_at.is_(None))
    if scope:
        statement = statement.where(ApiDefinition.scope == scope)
    return session.exec(statement).all()


def get_api_definition(session: Session, api_id: str) -> ApiDefinition | None:
    return session.get(ApiDefinition, api_id)


def create_custom_definition(session: Session, data: dict[str, Any]) -> ApiDefinition:
    obj = ApiDefinition(
        scope=ApiScope.custom,
        name=data["name"],
        method=data["method"].upper(),
        path=data["path"],
        description=data.get("description"),
        tags=data.get("tags", []),
        mode=ApiMode(data.get("mode") or "sql"),
        logic=data.get("logic"),
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_definition(session: Session, instance: ApiDefinition, data: dict[str, Any]) -> ApiDefinition:
    for key, value in data.items():
        if value is None:
            continue
        setattr(instance, key, value)
    instance.updated_at = datetime.utcnow()
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def soft_delete_definition(session: Session, instance: ApiDefinition) -> None:
    instance.deleted_at = datetime.utcnow()
    session.add(instance)
    session.commit()


def sync_system_definitions(session: Session, openapi_schema: dict[str, Any]) -> tuple[int, int]:
    synced = 0
    skipped = 0
    if not openapi_schema:
        return synced, skipped
    paths = openapi_schema.get("paths", {})
    for path, path_item in paths.items():
        for method, spec in path_item.items():
            method_upper = method.upper()
            if method_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            statement = select(ApiDefinition).where(
                ApiDefinition.method == method_upper,
                ApiDefinition.path == path,
                ApiDefinition.deleted_at.is_(None),
            )
            existing = session.exec(statement).scalar_one_or_none()
            description = spec.get("description") or spec.get("summary") or ""
            tags = spec.get("tags") or []
            if existing:
                existing.description = description
                existing.tags = tags
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                skipped += 1
            else:
                new_api = ApiDefinition(
                    scope=ApiScope.system,
                    name=spec.get("operationId") or f"{method_upper} {path}",
                    method=method_upper,
                    path=path,
                    description=description,
                    tags=tags,
                    mode=None,
                    logic=None,
                )
                session.add(new_api)
                synced += 1
    session.commit()
    return synced, skipped


def build_test_response(table: list[dict[str, Any]], summary: str, route: str) -> AnswerEnvelope:
    columns = list(table[0].keys()) if table else ["result"]
    rows = [
        [str(value) if value is not None else "" for value in row.values()]
        for row in table
    ]
    table_block = TableBlock(
        type="table",
        title="Test result",
        columns=columns,
        rows=rows or [["no results"]],
    )
    return AnswerEnvelope(
        meta=AnswerMeta(route=route, route_reason=summary, timing_ms=0, summary=summary),
        blocks=[MarkdownBlock(type="markdown", content=f"### {summary}"), table_block],
    )


def run_sql_logic(session: Session, logic: str) -> list[dict[str, Any]]:
    clean = logic.strip()
    if not clean.lower().startswith("select"):
        raise ValueError("Only SELECT statements are allowed for SQL mode")
    try:
        result = session.exec(text(clean))
        rows = [dict(row._mapping) for row in result]
        return rows
    except SQLAlchemyError as exc:
        raise
