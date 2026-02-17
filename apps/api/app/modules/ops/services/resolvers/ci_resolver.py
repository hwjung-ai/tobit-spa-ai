from __future__ import annotations

import re
from typing import Iterable

from app.modules.asset_registry.loader import load_query_asset, load_source_asset
from app.modules.inspector.asset_context import get_stage_assets, get_tracked_assets
from app.modules.ops.services.connections import ConnectionFactory

from .types import CIHit

CI_CODE_PATTERN = re.compile(
    r"\b(?:sys|srv|net|sto|sec|os|db|was|web|app|mes)-[a-z0-9-]+\b", re.IGNORECASE
)

def _resolve_source_ref(source_ref: str | None = None) -> str | None:
    if source_ref:
        return source_ref
    stage_assets = get_stage_assets()
    stage_source = stage_assets.get("source") if isinstance(stage_assets, dict) else None
    if isinstance(stage_source, dict) and stage_source.get("name"):
        return str(stage_source["name"])
    tracked_assets = get_tracked_assets()
    tracked_source = tracked_assets.get("source") if isinstance(tracked_assets, dict) else None
    if isinstance(tracked_source, dict) and tracked_source.get("name"):
        return str(tracked_source["name"])
    return None


def _get_connection(source_ref: str | None = None):
    """Get connection using explicitly selected source asset."""
    resolved_source_ref = _resolve_source_ref(source_ref)
    if not resolved_source_ref:
        raise ValueError("source_ref is required for CI resolver")
    source_asset = load_source_asset(resolved_source_ref)
    if not source_asset:
        raise ValueError(f"Source asset not found: {resolved_source_ref}")
    return ConnectionFactory.create(source_asset)


def _load_query(name: str) -> str:
    # Query assets must be managed in Asset Registry (DB).
    asset, _ = load_query_asset("ci", name.replace(".sql", ""))
    query = asset.get("sql") if asset else None
    if not query:
        raise ValueError(f"CI resolver query '{name}' not found in Asset Registry")
    return query


def resolve_ci(
    question: str,
    tenant_id: str | None = None,
    limit: int = 5,
    source_ref: str | None = None,
) -> list[CIHit]:
    """
    CI 해석: 3단계 검색 (우선도 기반)

    명시 CI코드가 있을 때:
    - 정확 매칭만 수행 (score 1.0)
    - 정확 매칭 성공 시 즉시 반환
    - 정확 매칭 실패 시 빈 리스트 반환 (no-data, broad search 금지)

    명시 CI코드가 없을 때:
    - ci_code 패턴 검색 (score 0.8)
    - ci_name 패턴 검색 (score 0.6)
    """
    resolved_tenant_id = tenant_id or "default"
    codes = _extract_codes(question)
    hits: list[CIHit] = []
    seen_codes: set[str] = set()

    connection = _get_connection(source_ref)
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        with conn.cursor() as cur:
            if codes:
                # 단계 1: 명시 CI코드의 정확 매칭만 수행
                exact_query = _load_query("ci_resolver_exact.sql")
                for code in dict.fromkeys(codes):
                    cur.execute(exact_query, (code, resolved_tenant_id, limit))
                    for row in cur.fetchall():
                        hits.append(_row_to_hit(row, 1.0))
                        seen_codes.add(row[1])
                        if len(hits) >= limit:
                            return hits

                # 명시 CI코드가 있는데 정확 매칭 결과가 있으면 그것만 반환
                if hits:
                    return hits

                # 명시 CI코드가 있는데 정확 매칭 실패 → no-data (빈 리스트)
                # broad search(ci_code/ci_name 패턴)로 폴백하지 않음
                return []

            # 명시 CI코드가 없을 때만 broad search 진행
            # 단계 2: ci_code 패턴 검색
            remaining = limit - len(hits)
            if remaining > 0:
                for row in _query_pattern(
                    cur, resolved_tenant_id, question, "ci_code", remaining
                ):
                    if row[1] in seen_codes:
                        continue
                    hits.append(_row_to_hit(row, 0.8))
                    seen_codes.add(row[1])
                    if len(hits) >= limit:
                        return hits

            # 단계 3: ci_name 패턴 검색
            remaining = limit - len(hits)
            if remaining > 0:
                for row in _query_pattern(
                    cur, resolved_tenant_id, question, "ci_name", remaining
                ):
                    if row[1] in seen_codes:
                        continue
                    hits.append(_row_to_hit(row, 0.6))

    finally:
        connection.close()

    return hits


def _extract_codes(question: str) -> list[str]:
    return [match.group(0).lower() for match in CI_CODE_PATTERN.finditer(question)]


def _query_pattern(
    cur, tenant_id: str, question: str, field: str, limit: int
) -> list[tuple]:
    term = _primary_term(question)
    if not term:
        return []
    if field not in {"ci_code", "ci_name"}:
        raise ValueError("Unsupported field for CI query")
    pattern_query = _load_query("ci_resolver_pattern.sql").format(field=field)
    cur.execute(pattern_query, (tenant_id, f"%{term}%", limit))
    return cur.fetchall()


def _primary_term(question: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", question.lower())
    tokens = sorted(tokens, key=len, reverse=True)
    return tokens[0] if tokens else ""


def _row_to_hit(row: Iterable[str], score: float) -> CIHit:
    ci_id, ci_code, ci_name, ci_type, ci_subtype, ci_category = row
    return CIHit(
        ci_id=str(ci_id),
        ci_code=ci_code,
        ci_name=ci_name,
        ci_type=ci_type,
        ci_subtype=ci_subtype,
        ci_category=ci_category,
        score=score,
    )
