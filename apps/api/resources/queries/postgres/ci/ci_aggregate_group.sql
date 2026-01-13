SELECT {select_clause}, {metric_clause}
FROM ci
WHERE {where_clause}
GROUP BY {group_clause}
{order_by_clause}
LIMIT %s
