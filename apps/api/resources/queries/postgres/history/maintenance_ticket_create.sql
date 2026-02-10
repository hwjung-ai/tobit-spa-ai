-- Create Maintenance Ticket
-- Creates a new maintenance ticket record
-- Parameters: id (uuid), tenant_id, ci_id (uuid), maint_type, summary, detail, start_time, performer

INSERT INTO maintenance_history (
    id,
    tenant_id,
    ci_id,
    maint_type,
    summary,
    detail,
    start_time,
    end_time,
    duration_min,
    performer,
    result,
    created_at
) VALUES (
    %s::uuid,
    %s,
    %s::uuid,
    %s,
    %s,
    %s,
    %s::timestamp,
    NULL,
    0,
    %s,
    'Scheduled',
    NOW()
)
RETURNING id, created_at
