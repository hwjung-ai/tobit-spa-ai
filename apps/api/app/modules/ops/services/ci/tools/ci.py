from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal

from psycopg import Connection

from apps.api.scripts.seed.utils import get_postgres_conn

from app.shared.config_loader import load_text

SEARCH_COLUMNS = ["ci_code", "ci_name", "ci_type", "ci_subtype", "ci_category"]
FILTER_FIELDS = {"ci_type", "ci_subtype", "ci_category", "status", "location", "owner"}
JSONB_TAG_KEYS = {"system", "role", "runs_on", "host_server", "ci_subtype", "connected_servers"}
JSONB_ATTR_KEYS = {"engine", "version", "zone", "ip", "cpu_cores", "memory_gb"}
MAX_SEARCH_LIMIT = 50
MAX_AGG_ROWS = 200
AGG_METRICS = {"count", "count_distinct"}

_QUERY_BASE = "queries/postgres/ci"


def _load_query(name: str) -> str:
    query = load_text(f"{_QUERY_BASE}/{name}")
    if not query:
        raise ValueError(f"CI query '{name}' not found")
    return query

FilterOp = Literal["=", "!=", "ILIKE"]


class FilterSpec(Dict[str, Any]):
    field: str
    op: FilterOp
    value: str


def _clamp_limit(value: int | None, default: int, max_value: int) -> int:
    if value is None:
        return default
    return max(1, min(max_value, value))


def _build_filter_clauses(filters: Iterable[FilterSpec], params: List[Any]) -> List[str]:
    clauses: List[str] = []
    for spec in filters:
        field = spec.get("field")
        if not field:
            continue
        op = spec.get("op", "=").upper()
        value = spec.get("value")
        if op not in {"=", "!=", "ILIKE"}:
            raise ValueError(f"Unsupported filter operator '{op}'")
        if "." in field:
            prefix, key = field.split(".", 1)
            if prefix not in {"tags", "attributes"}:
                raise ValueError(f"Invalid JSONB prefix '{prefix}' for filter")
            allowlist = JSONB_TAG_KEYS if prefix == "tags" else JSONB_ATTR_KEYS
            if key not in allowlist:
                raise ValueError(f"JSONB key '{key}' is not allowed for {prefix}")
            column = f"{prefix}->>%s"
            clause = f"{column} {op} %s"
            clauses.append(clause)
            params.extend([key, value])
        else:
            if field not in FILTER_FIELDS:
                raise ValueError(f"Filter field '{field}' is not allowed")
            clause = f"ci.{field} {op} %s"
            clauses.append(clause)
            params.append(value)
    return clauses


def _build_keyword_clause(keywords: Iterable[str], params: List[Any]) -> List[str]:
    clauses: List[str] = []
    for keyword in keywords:
        normalized = keyword.strip()
        if not normalized:
            continue
        pattern = f"%{normalized}%"
        field_clauses = [f"(ci.{column})::text ILIKE %s" for column in SEARCH_COLUMNS]
        clauses.append(f"({' OR '.join(field_clauses)})")
        params.extend([pattern] * len(field_clauses))
    return clauses


def _build_keyword_clause_or(keywords: Iterable[str], params: List[Any]) -> str | None:
    groups = _build_keyword_clause(keywords, params)
    if not groups:
        return None
    return f"({' OR '.join(groups)})"


def ci_search(
    tenant_id: str,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = 10,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> List[Dict[str, Any]]:
    sanitized_limit = _clamp_limit(limit, 10, MAX_SEARCH_LIMIT)
    with get_postgres_conn() as conn:
        return _ci_search_inner(conn, tenant_id, keywords or (), filters or (), sanitized_limit, sort)


def ci_search_broad_or(
    tenant_id: str,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = 10,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> List[Dict[str, Any]]:
    sanitized_limit = _clamp_limit(limit, 10, MAX_SEARCH_LIMIT)
    with get_postgres_conn() as conn:
        return _ci_search_broad_or_inner(conn, tenant_id, keywords or (), filters or (), sanitized_limit, sort)


def _ci_search_broad_or_inner(
    conn: Connection,
    tenant_id: str,
    keywords: Iterable[str],
    filters: Iterable[FilterSpec],
    limit: int,
    sort: tuple[str, Literal["ASC", "DESC"]] | None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [tenant_id]
    where_clauses = ["ci.tenant_id = %s"]
    where_clauses.extend(_build_filter_clauses(filters, params))
    keyword_or = _build_keyword_clause_or(keywords, params)
    if keyword_or:
        where_clauses.append(keyword_or)
    order_by = "ci.ci_code"
    direction = "ASC"
    if sort:
        column, dir_value = sort
        if column not in SEARCH_COLUMNS:
            raise ValueError(f"Sort column '{column}' is not allowed")
        order_by = f"ci.{column}"
        direction = dir_value
    query_template = _load_query("ci_search.sql")
    query = query_template.format(
        where_clause=" AND ".join(where_clauses),
        order_by=order_by,
        direction=direction,
    )
    params.append(limit)
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = [
            {
                "ci_id": str(row[0]),
                "ci_code": row[1],
                "ci_name": row[2],
                "ci_type": row[3],
                "ci_subtype": row[4],
                "ci_category": row[5],
                "status": row[6],
                "location": row[7],
                "owner": row[8],
            }
            for row in cur.fetchall()
        ]
    return rows


def _ci_search_inner(
    conn: Connection,
    tenant_id: str,
    keywords: Iterable[str],
    filters: Iterable[FilterSpec],
    limit: int,
    sort: tuple[str, Literal["ASC", "DESC"]] | None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [tenant_id]
    where_clauses = ["ci.tenant_id = %s"]
    where_clauses.extend(_build_filter_clauses(filters, params))
    where_clauses.extend(_build_keyword_clause(keywords, params))
    order_by = "ci.ci_code"
    direction = "ASC"
    if sort:
        column, dir_value = sort
        if column not in SEARCH_COLUMNS:
            raise ValueError(f"Sort column '{column}' is not allowed")
        order_by = f"ci.{column}"
        direction = dir_value
    query_template = _load_query("ci_search.sql")
    query = query_template.format(
        where_clause=" AND ".join(where_clauses),
        order_by=order_by,
        direction=direction,
    )
    params.append(limit)
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = [
            {
                "ci_id": str(row[0]),
                "ci_code": row[1],
                "ci_name": row[2],
                "ci_type": row[3],
                "ci_subtype": row[4],
                "ci_category": row[5],
                "status": row[6],
                "location": row[7],
                "owner": row[8],
            }
            for row in cur.fetchall()
        ]
    return rows


def ci_get(tenant_id: str, ci_id: str) -> Dict[str, Any] | None:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            query = _load_query("ci_get.sql").format(field="ci_id")
            cur.execute(query, (ci_id, tenant_id))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "ci_id": str(row[0]),
                "ci_code": row[1],
                "ci_name": row[2],
                "ci_type": row[3],
                "ci_subtype": row[4],
                "ci_category": row[5],
                "status": row[6],
                "location": row[7],
                "owner": row[8],
                "tags": row[9] or {},
                "attributes": row[10] or {},
            }


def ci_get_by_code(tenant_id: str, ci_code: str) -> Dict[str, Any] | None:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            query = _load_query("ci_get.sql").format(field="ci_code")
            cur.execute(query, (ci_code, tenant_id))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "ci_id": str(row[0]),
                "ci_code": row[1],
                "ci_name": row[2],
                "ci_type": row[3],
                "ci_subtype": row[4],
                "ci_category": row[5],
                "status": row[6],
                "location": row[7],
                "owner": row[8],
                "tags": row[9] or {},
                "attributes": row[10] or {},
            }


def ci_aggregate(
    tenant_id: str,
    group_by: Iterable[str],
    metrics: Iterable[str],
    filters: Iterable[FilterSpec] | None = None,
    ci_ids: Iterable[str] | None = None,
    top_n: int | None = 50,
) -> Dict[str, Any]:
    group_list = [field for field in group_by if field in FILTER_FIELDS]
    metric_list = [metric for metric in metrics if metric in AGG_METRICS]
    if not metric_list:
        raise ValueError("At least one valid metric is required")
    sanitized_limit = _clamp_limit(top_n, 50, MAX_AGG_ROWS)
    params: List[Any] = [tenant_id]
    where_clauses = ["ci.tenant_id = %s"]
    if ci_ids:
        where_clauses.append("ci.ci_id = ANY(%s)")
        params.append(list(ci_ids))
    where_clauses.extend(_build_filter_clauses(filters or (), params))
    metric_clause = []
    for metric in metric_list:
        if metric == "count":
            metric_clause.append("COUNT(*) AS count")
        elif metric == "count_distinct":
            metric_clause.append("COUNT(DISTINCT ci.ci_id) AS count_distinct")
    group_clause = ", ".join(f"ci.{field}" for field in group_list)
    order_by_clause = "ORDER BY count DESC" if group_list and "count" in metric_list else ""
    where_clause = " AND ".join(where_clauses)
    if group_list:
        select_clause = ", ".join(f"ci.{field}" for field in group_list)
        columns = [field for field in group_list] + metric_list
        query_template = _load_query("ci_aggregate_group.sql")
        query = query_template.format(
            select_clause=select_clause,
            metric_clause=", ".join(metric_clause),
            where_clause=where_clause,
            group_clause=group_clause,
            order_by_clause=order_by_clause,
        )
    else:
        columns = metric_list
        query_template = _load_query("ci_aggregate_total.sql")
        query = query_template.format(
            metric_clause=", ".join(metric_clause),
            where_clause=where_clause,
        )
    count_query = _load_query("ci_aggregate_count.sql").format(where_clause=where_clause)
    count_params = list(params)
    query_params = params + [sanitized_limit] if group_list else params
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(count_query, count_params)
            total_count = cur.fetchone()[0]
            cur.execute(query, query_params)
            columns = [field for field in group_list] + metric_list
            rows: List[List[str]] = []
            for row in cur.fetchall():
                rendered = [str(row[idx]) for idx in range(len(columns))]
                rows.append(rendered)
    query_str = query.strip()
    return {
        "columns": columns,
        "rows": rows,
        "total": len(rows),
        "total_count": total_count,
        "query": query_str,
        "params": query_params,
    }


def ci_list_preview(
    tenant_id: str,
    limit: int,
    offset: int = 0,
    filters: Iterable[FilterSpec] | None = None,
) -> Dict[str, Any]:
    sanitized_limit = _clamp_limit(limit, 50, 50)
    sanitized_offset = max(0, offset)
    params: List[Any] = [tenant_id]
    where_clauses = ["ci.tenant_id = %s"]
    where_clauses.extend(_build_filter_clauses(filters or (), params))
    total_params = list(params)
    where_clause = " AND ".join(where_clauses)
    total_query = _load_query("ci_aggregate_count.sql").format(where_clause=where_clause)
    query_template = _load_query("ci_list_preview.sql")
    query = query_template.format(where_clause=where_clause)
    params.extend([sanitized_limit, sanitized_offset])
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(total_query, total_params)
            total = cur.fetchone()[0]
            cur.execute(query, params)
            rows = [
                {
                    "ci_id": str(row[0]),
                    "ci_code": row[1],
                    "ci_name": row[2],
                    "ci_type": row[3],
                    "ci_subtype": row[4],
                    "status": row[5],
                    "owner": row[6],
                    "location": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                }
                for row in cur.fetchall()
            ]
    return {
        "rows": rows,
        "total": total,
        "limit": sanitized_limit,
        "offset": sanitized_offset,
    }
