# LLM Call Log - Implementation Guide

## Overview

The LLM Call Log system provides comprehensive tracking of all LLM API calls for debugging, analytics, and cost monitoring.

## What Was Implemented

### 1. Database Schema (`tb_llm_call_log`)

```sql
CREATE TABLE tb_llm_call_log (
    id UUID PRIMARY KEY,
    trace_id UUID REFERENCES tb_execution_trace(trace_id),
    call_type TEXT NOT NULL,           -- 'planner', 'output_parser', 'tool', etc
    call_index INTEGER DEFAULT 1,       -- For ordering multiple calls

    -- Input
    system_prompt TEXT,
    user_prompt TEXT,
    context JSON,                       -- Asset versions, tools, etc

    -- Output
    raw_response TEXT,                  -- Full LLM response
    parsed_response JSON,               -- Parsed result (Plan, tool_calls)

    -- Metadata
    model_name TEXT NOT NULL,           -- 'gpt-4o', 'claude-3-5-sonnet', etc
    provider TEXT,                      -- 'openai', 'anthropic', 'google'
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,

    -- Timing
    request_time TIMESTAMP NOT NULL,
    response_time TIMESTAMP,
    duration_ms INTEGER DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'success',      -- 'success', 'error', 'timeout'
    error_message TEXT,
    error_details JSON,

    -- Feature context
    feature TEXT,                       -- 'ops', 'docs', 'cep'
    ui_endpoint TEXT,                   -- '/ops/ask', '/ops/query'
    user_id UUID,

    -- Analytics
    tags JSON,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Files Created

| File | Description |
|------|-------------|
| `apps/api/alembic/versions/0052_add_llm_call_log.py` | Database migration |
| `apps/api/app/modules/llm/models.py` | SQLAlchemy models |
| `apps/api/app/modules/llm/crud.py` | CRUD operations |
| `apps/api/app/modules/llm/router.py` | API endpoints |
| `apps/api/app/modules/llm/__init__.py` | Module exports |
| `apps/api/app/llm/client.py` (updated) | LLM client with logging |
| `apps/web/src/app/admin/llm-logs/page.tsx` | UI page |

### 3. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/llm-logs` | GET | List LLM call logs with filters |
| `/admin/llm-logs/pairs` | GET | Get logs grouped as query-response pairs |
| `/admin/llm-logs/analytics` | GET | Get analytics summary |
| `/admin/llm-logs/{log_id}` | GET | Get detailed log by ID |
| `/admin/llm-logs/trace/{trace_id}` | GET | Get all logs for a trace |

### 4. LLMCallLogger Usage

The `LlmCallLogger` context manager automatically logs LLM calls:

```python
from app.llm.client import LlmCallLogger
from uuid import uuid4

async with LlmCallLogger(
    session=session,
    call_type="planner",
    model_name="gpt-4o",
    trace_id=trace_id,
    feature="ops",
    ui_endpoint="/ops/ask",
) as logger:
    logger.set_prompts(
        system_prompt=system_msg,
        user_prompt=user_msg
    )

    response = await llm.acreate_response(
        model="gpt-4o",
        input=messages
    )

    logger.log_response(
        response=response,
        parsed_response={"plan": plan}
    )
# Automatically saves to database when exiting context
```

### 5. UI Features

**Admin > LLM Logs** page provides:

1. **Analytics Cards**:
   - Total calls (success/error breakdown)
   - Total tokens (input/output)
   - Average latency
   - Top model

2. **Filters**:
   - Status (All, Success, Error)
   - Call Type (All, Planner, Output Parser, Tool)
   - Feature (All, OPS, Docs, CEP)

3. **Logs Table**:
   - Timestamp
   - Call type (with badge)
   - Model name
   - Tokens (formatted: 1.2M, 45K)
   - Duration (formatted: 2.5s, 450ms)
   - Status badge
   - Feature

4. **Detail Modal**:
   - User prompt
   - System prompt
   - Raw LLM response
   - Context (asset versions, tools)
   - Error details
   - Metadata (trace ID, UI endpoint, provider)

## Migration

To apply the database migration:

```bash
cd apps/api
alembic upgrade head
```

## Analytics

The analytics endpoint provides:

```json
{
  "total_calls": 1250,
  "successful_calls": 1200,
  "failed_calls": 50,
  "total_input_tokens": 2500000,
  "total_output_tokens": 500000,
  "total_tokens": 3000000,
  "avg_latency_ms": 1250.5,
  "total_duration_ms": 1563125,
  "model_breakdown": {
    "gpt-4o": 800,
    "claude-3-5-sonnet-20241022": 400,
    "gpt-4o-mini": 50
  },
  "feature_breakdown": {
    "ops": 900,
    "docs": 250,
    "cep": 100
  },
  "call_type_breakdown": {
    "planner": 600,
    "output_parser": 500,
    "tool": 150
  }
}
```

## Future Enhancements

1. **Cost Tracking**: Add estimated cost per call based on model pricing
2. **Trends**: Show token usage over time with charts
3. **Alerts**: Notify when token usage exceeds thresholds
4. **Export**: Allow exporting logs as CSV/JSON
5. **Comparison**: Compare traces side-by-side
6. **Token Optimization**: Suggest prompt improvements to reduce tokens

## Notes

- Logs are stored indefinitely; consider implementing retention policies
- Sensitive data in prompts (API keys, secrets) should be masked
- Large prompts/responses (>1MB) may impact performance
