SELECT ci.ci_id, ci.ci_code, ci.ci_name, ci.ci_type, ci.ci_subtype, ci.ci_category,
       ci.status, ci.location, ci.owner, ci_ext.tags, ci_ext.attributes
FROM ci
LEFT JOIN ci_ext ON ci.ci_id = ci_ext.ci_id
WHERE ci.{field} = %s AND ci.tenant_id = %s
