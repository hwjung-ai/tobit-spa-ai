from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal

from psycopg import Connection
from schemas.tool_contracts import (
    CIAggregateResult,
    CIListResult,
    CIRecord,
    CISearchResult,
)

from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
    ToolType,
)
from app.shared.config_loader import load_text
from app.modules.asset_registry.loader import load_source_asset
from app.modules.ops.services.connections import ConnectionFactory
from core.config import get_settings

SEARCH_COLUMNS = ["ci_code", "ci_name", "ci_type", "ci_subtype", "ci_category"]
FILTER_FIELDS = {"ci_type", "ci_subtype", "ci_category", "status", "location", "owner"}
JSONB_TAG_KEYS = {
    "system",
    "role",
    "runs_on",
    "host_server",
    "ci_subtype",
    "connected_servers",
}
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


def _get_connection():
    """Get connection for CI operations using source asset."""
    settings = get_settings()
    source_asset = load_source_asset(settings.ops_default_source_asset)
    return ConnectionFactory.create(source_asset)


FilterOp = Literal["=", "!=", "ILIKE"]


class FilterSpec(Dict[str, Any]):
    field: str
    op: FilterOp
    value: str


def _clamp_limit(value: int | None, default: int, max_value: int) -> int:
    if value is None:
        return default
    return max(1, min(max_value, value))


def _build_filter_clauses(
    filters: Iterable[FilterSpec], params: List[Any]
) -> List[str]:
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
) -> CISearchResult:
    sanitized_limit = _clamp_limit(limit, 10, MAX_SEARCH_LIMIT)
    connection = _get_connection()
    try:
        # For PostgreSQL connection, get the underlying psycopg connection
        conn = connection.connection if hasattr(connection, 'connection') else connection
        rows = _ci_search_inner(
            conn, tenant_id, keywords or (), filters or (), sanitized_limit, sort
        )
        records = [CIRecord(**row) for row in rows]
        return CISearchResult(
            records=records,
            total=len(records),
            query=None,
            params=[],
        )
    finally:
        connection.close()


def ci_search_broad_or(
    tenant_id: str,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = 10,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> CISearchResult:
    sanitized_limit = _clamp_limit(limit, 10, MAX_SEARCH_LIMIT)
    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        rows = _ci_search_broad_or_inner(
            conn, tenant_id, keywords or (), filters or (), sanitized_limit, sort
        )
        records = [CIRecord(**row) for row in rows]
        return CISearchResult(
            records=records,
            total=len(records),
            query=None,
            params=[],
        )
    finally:
        connection.close()


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


def ci_get(tenant_id: str, ci_id: str) -> CIRecord | None:
    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        with conn.cursor() as cur:
            query = _load_query("ci_get.sql").format(field="ci_id")
            cur.execute(query, (ci_id, tenant_id))
            row = cur.fetchone()
            if not row:
                return None
            return CIRecord(
                ci_id=str(row[0]),
                ci_code=row[1],
                ci_name=row[2],
                ci_type=row[3],
                ci_subtype=row[4],
                ci_category=row[5],
                status=row[6],
                location=row[7],
                owner=row[8],
                tags=row[9] or {},
                attributes=row[10] or {},
            )
    finally:
        connection.close()


def ci_get_by_code(tenant_id: str, ci_code: str) -> CIRecord | None:
    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        with conn.cursor() as cur:
            query = _load_query("ci_get.sql").format(field="ci_code")
            cur.execute(query, (ci_code, tenant_id))
            row = cur.fetchone()
            if not row:
                return None
            return CIRecord(
                ci_id=str(row[0]),
                ci_code=row[1],
                ci_name=row[2],
                ci_type=row[3],
                ci_subtype=row[4],
                ci_category=row[5],
                status=row[6],
                location=row[7],
                owner=row[8],
                tags=row[9] or {},
                attributes=row[10] or {},
            )
    finally:
        connection.close()


def ci_aggregate(
    tenant_id: str,
    group_by: Iterable[str],
    metrics: Iterable[str],
    filters: Iterable[FilterSpec] | None = None,
    ci_ids: Iterable[str] | None = None,
    top_n: int | None = 50,
) -> CIAggregateResult:
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
    order_by_clause = (
        "ORDER BY count DESC" if group_list and "count" in metric_list else ""
    )
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
    count_query = _load_query("ci_aggregate_count.sql").format(
        where_clause=where_clause
    )
    count_params = list(params)
    query_params = params + [sanitized_limit] if group_list else params

    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        with conn.cursor() as cur:
            cur.execute(count_query, count_params)
            cur.fetchone()[0]
            cur.execute(query, query_params)
            columns = [field for field in group_list] + metric_list
            rows: List[List[str]] = []
            for row in cur.fetchall():
                rendered = [str(row[idx]) for idx in range(len(columns))]
                rows.append(rendered)
    finally:
        connection.close()

    query_str = query.strip()
    return CIAggregateResult(
        columns=columns,
        rows=rows,
        total=len(rows),
        query=query_str,
        params=query_params,
    )


def ci_list_preview(
    tenant_id: str,
    limit: int,
    offset: int = 0,
    filters: Iterable[FilterSpec] | None = None,
) -> CIListResult:
    sanitized_limit = _clamp_limit(limit, 50, 50)
    sanitized_offset = max(0, offset)
    params: List[Any] = [tenant_id]
    where_clauses = ["ci.tenant_id = %s"]
    where_clauses.extend(_build_filter_clauses(filters or (), params))
    total_params = list(params)
    where_clause = " AND ".join(where_clauses)
    total_query = _load_query("ci_aggregate_count.sql").format(
        where_clause=where_clause
    )
    query_template = _load_query("ci_list_preview.sql")
    query = query_template.format(where_clause=where_clause)
    params.extend([sanitized_limit, sanitized_offset])

    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
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
    finally:
        connection.close()

    return CIListResult(
        rows=rows,
        total=total,
        limit=sanitized_limit,
        offset=sanitized_offset,
        query=query.strip(),
        params=params,
    )


# ==============================================================================
# Tool Interface Implementation
# ==============================================================================


class CITool(BaseTool):
    """
    Tool for CI (Configuration Item) operations.

    Provides methods to search, retrieve, aggregate, and list CI configuration items
    from the PostgreSQL database. Supports keyword search, filtering, and various
    aggregation operations.
    """

    @property
    def tool_type(self) -> ToolType:
        """Return the CI tool type."""
        return ToolType.CI

    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute for the given operation.

        CI tool handles operations with these parameter keys:
        - operation: 'search', 'search_broad_or', 'get', 'get_by_code', 'aggregate', 'list_preview'

        Args:
            context: Execution context
            params: Tool parameters

        Returns:
            True if this is a CI operation, False otherwise
        """
        operation = params.get("operation", "")
        valid_operations = {
            "search",
            "search_broad_or",
            "get",
            "get_by_code",
            "aggregate",
            "list_preview",
        }
        return operation in valid_operations

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a CI operation.

        Dispatches to the appropriate function based on the 'operation' parameter.

        Parameters:
            operation (str): The operation to perform
            keywords (list[str], optional): Keywords for search
            filters (list[dict], optional): Filter specifications
            limit (int, optional): Result limit
            offset (int, optional): Result offset
            sort (tuple, optional): Sort specification
            ci_id (str, optional): CI ID for retrieval or aggregation
            ci_code (str, optional): CI code for retrieval
            ci_ids (list[str], optional): Multiple CI IDs for aggregation
            group_by (list[str], optional): Grouping fields for aggregation
            metrics (list[str], optional): Metrics for aggregation
            top_n (int, optional): Top N results for aggregation

        Returns:
            ToolResult with success status and operation result
        """
        try:
            operation = params.get("operation", "")
            tenant_id = context.tenant_id

            if operation == "search":
                result = ci_search(
                    tenant_id=tenant_id,
                    keywords=params.get("keywords"),
                    filters=params.get("filters"),
                    limit=params.get("limit", 10),
                    sort=params.get("sort"),
                )
            elif operation == "search_broad_or":
                result = ci_search_broad_or(
                    tenant_id=tenant_id,
                    keywords=params.get("keywords"),
                    filters=params.get("filters"),
                    limit=params.get("limit", 10),
                    sort=params.get("sort"),
                )
            elif operation == "get":
                result = ci_get(tenant_id=tenant_id, ci_id=params["ci_id"])
                if result is None:
                    return ToolResult(
                        success=False,
                        error=f"CI with ID '{params['ci_id']}' not found",
                    )
            elif operation == "get_by_code":
                result = ci_get_by_code(tenant_id=tenant_id, ci_code=params["ci_code"])
                if result is None:
                    return ToolResult(
                        success=False,
                        error=f"CI with code '{params['ci_code']}' not found",
                    )
            elif operation == "aggregate":
                result = ci_aggregate(
                    tenant_id=tenant_id,
                    group_by=params.get("group_by", []),
                    metrics=params.get("metrics", []),
                    filters=params.get("filters"),
                    ci_ids=params.get("ci_ids"),
                    top_n=params.get("top_n", 50),
                )
            elif operation == "list_preview":
                result = ci_list_preview(
                    tenant_id=tenant_id,
                    limit=params.get("limit", 50),
                    offset=params.get("offset", 0),
                    filters=params.get("filters"),
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown CI operation: {operation}",
                )

            return ToolResult(success=True, data=result)

        except ValueError as e:
            return await self.format_error(context, e, params)
        except Exception as e:
            return await self.format_error(context, e, params)


# Create and register the CI tool
_ci_tool = CITool()
