# OPS Orchestration API Documentation

## Overview

This document provides comprehensive API documentation for the OPS orchestration system, including all endpoints and data models introduced in Phase 3 and Phase 4.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require authentication via API keys. Include the following header in your requests:

```http
Authorization: Bearer <your-api-key>
```

## Endpoints

### 1. CI Orchestration Endpoints

#### POST /ops/ci/ask

Execute a CI orchestration query.

**Request Body:**
```json
{
  "question": "서버 상태를 확인해주세요",
  "context": {
    "test_mode": false,
    "asset_overrides": {}
  }
}
```

**Response:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "blocks": [
      {
        "type": "table",
        "content": {
          "headers": ["Server", "Status"],
          "rows": [["srv-erp-01", "active"]]
        }
      }
    ],
    "meta": {
      "route": "orch",
      "duration_ms": 1234,
      "used_tools": ["ci_lookup"]
    },
    "trace": {
      "trace_id": "abc123...",
      "route": "orch",
      "stage_inputs": [...],
      "stage_outputs": [...],
      "replan_events": [...]
    }
  }
}
```

### 2. Inspector Endpoints

#### GET /inspector/traces

List execution traces with filtering and pagination.

**Query Parameters:**
- `q` (string, optional): Search text for question/feature/endpoint
- `feature` (string, optional): Filter by feature
- `status` (string, optional): Filter by status
- `from` (datetime, optional): Start timestamp
- `to` (datetime, optional): End timestamp
- `limit` (int, default=20): Number of results to return
- `offset` (int, default=0): Offset for pagination
- `route` (string, optional): Filter by route: direct, orch, reject

**Response:**
```json
{
  "code": 0,
  "data": {
    "traces": [
      {
        "trace_id": "abc123...",
        "created_at": "2026-01-22T10:00:00Z",
        "feature": "server_status",
        "status": "success",
        "duration_ms": 1234,
        "question_snippet": "서버 상태를 확인해주세요",
        "applied_asset_versions": ["prompt:server-check:1.0.0"]
      }
    ],
    "total": 100,
    "limit": 20,
    "offset": 0
  }
}
```

#### GET /inspector/traces/{trace_id}

Get detailed trace information.

**Response:**
```json
{
  "code": 0,
  "data": {
    "trace": {
      "trace_id": "abc123...",
      "question": "서버 상태를 확인해주세요",
      "route": "orch",
      "created_at": "2026-01-22T10:00:00Z",
      "duration_ms": 1234,
      "status": "success",
      "stage_inputs": [
        {
          "stage": "route_plan",
          "applied_assets": {
            "prompt": "prompt:server-check:1.0.0"
          },
          "params": {
            "question": "서버 상태를 확인해주세요"
          }
        }
      ],
      "stage_outputs": [
        {
          "stage": "route_plan",
          "result": {
            "plan_output": {...},
            "route": "orch"
          },
          "diagnostics": {
            "status": "ok",
            "warnings": [],
            "errors": [],
            "empty_flags": {},
            "counts": {}
          },
          "references": [],
          "duration_ms": 150
        }
      ],
      "replan_events": [
        {
          "event_type": "replan_decision",
          "stage_name": "execute",
          "trigger": {
            "trigger_type": "timeout",
            "reason": "Execution timeout",
            "severity": "medium"
          },
          "patch": {
            "before": {...},
            "after": {...}
          },
          "timestamp": "2026-01-22T10:00:15Z",
          "decision_metadata": {
            "should_replan": false,
            "evaluation_time": 0.123
          }
        }
      ]
    },
    "audit_logs": [
      {
        "id": "log123...",
        "trace_id": "abc123...",
        "resource_type": "stage",
        "resource_id": "route_plan",
        "action": "executed",
        "timestamp": "2026-01-22T10:00:00Z"
      }
    ]
  }
}
```

#### POST /inspector/traces/{trace_id}/ui-render

Store UI render information for a trace.

**Request Body:**
```json
{
  "blocks": [...],
  "meta": {...}
}
```

### 3. Regression Analysis Endpoints

#### POST /inspector/regression/analyze

Perform regression analysis between two traces.

**Request Body:**
```json
{
  "type": "stage",
  "baseline_trace_id": "baseline123...",
  "comparison_trace_id": "comparison123...",
  "parameters": {
    "stages": ["route_plan", "validate", "execute", "compose", "present"]
  }
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "analysis_id": "reg_analysis_123...",
    "type": "stage",
    "baseline_trace_id": "baseline123...",
    "comparison_trace_id": "comparison123...",
    "started_at": "2026-01-22T10:00:00Z",
    "completed_at": "2026-01-22T10:00:30Z",
    "status": "completed",
    "stage_reports": [
      {
        "stage_name": "execute",
        "baseline_metrics": {
          "stage_name": "execute",
          "duration_ms": 1000,
          "status": "ok",
          "reference_count": 10
        },
        "current_metrics": {
          "stage_name": "execute",
          "duration_ms": 1500,
          "status": "warning",
          "reference_count": 8
        },
        "differences": {
          "duration_ms": 500,
          "reference_count": -2
        },
        "regression_score": 70,
        "issues": ["Performance degraded"],
        "recommendations": ["Investigate performance issue"]
      }
    ],
    "overall_regression_score": 75,
    "significant_changes": 2,
    "critical_issues": ["Critical regression in execute stage"],
    "summary": "2 stages showed significant changes",
    "recommendations": ["Investigate root cause"]
  }
}
```

#### GET /inspector/regression/{analysis_id}

Get regression analysis by ID.

**Response:**
```json
{
  "code": 0,
  "data": {
    "analysis_id": "reg_analysis_123...",
    "type": "stage",
    "baseline_trace_id": "baseline123...",
    "comparison_trace_id": "comparison123...",
    "started_at": "2026-01-22T10:00:00Z",
    "completed_at": "2026-01-22T10:00:30Z",
    "status": "completed",
    "stage_reports": [...],
    "overall_regression_score": 75,
    "significant_changes": 2,
    "critical_issues": [...],
    "summary": "...",
    "recommendations": [...]
  }
}
```

#### POST /inspector/regression/stage-compare

Compare stages between two traces directly.

**Request Body:**
```json
{
  "baseline_trace_id": "baseline123...",
  "comparison_trace_id": "comparison123...",
  "stages": ["execute", "compose"]
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "baseline_trace": {...},
    "comparison_trace": {...},
    "stage_differences": {
      "execute": {
        "duration_difference_ms": 500,
        "status_changed": true,
        "baseline_metrics": {...},
        "comparison_metrics": {...}
      }
    },
    "regression_scores": {
      "execute": 70,
      "compose": 85
    },
    "overall_assessment": "Moderate regression detected in 1 stages"
  }
}
```

### 4. Asset Registry Endpoints

#### GET /assets/{asset_type}

List assets of a specific type.

**Query Parameters:**
- `type` (string): Asset type (prompt, policy, query, mapping, screen)
- `version` (string, optional): Filter by version
- `status` (string, optional): Filter by status

**Response:**
```json
{
  "code": 0,
  "data": {
    "assets": [
      {
        "id": "asset_123...",
        "asset_id": "server-check",
        "version": "1.0.0",
        "name": "Server Check Prompt",
        "description": "Checks server status and health",
        "created_at": "2026-01-22T10:00:00Z",
        "status": "published",
        "author": "ops-team",
        "metadata": {
          "category": "monitoring",
          "tags": ["server", "health"]
        }
      }
    ],
    "total": 50
  }
}
```

### 5. Control Loop Endpoints

#### GET /ops/control-loop/stats

Get control loop statistics.

**Response:**
```json
{
  "code": 0,
  "data": {
    "replan_count": 3,
    "max_replans": 5,
    "last_replan_time": "2026-01-22T10:00:00Z",
    "replan_history_count": 3,
    "trigger_counts": {
      "error": 1,
      "timeout": 2
    },
    "policy": {
      "max_replans": 5,
      "allowed_triggers": ["error", "timeout", "policy_violation"],
      "enable_automatic_replan": true,
      "min_interval_seconds": 60,
      "cooling_period_seconds": 300
    }
  }
}
```

## Data Models

### PlanOutput

```python
class PlanOutputKind(str, Enum):
    DIRECT = "direct"
    PLAN = "plan"
    REJECT = "reject"

class PlanOutput(BaseModel):
    kind: PlanOutputKind
    direct_answer: Optional[DirectAnswerPayload] = None
    plan: Optional[Plan] = None
    reject_reason: Optional[str] = None
    reject_policy: Optional[str] = None
    confidence: float = 1.0
    reasoning: Optional[str] = None
```

### StageInput/StageOutput

```python
class StageInput(BaseModel):
    stage: str  # "route_plan" | "validate" | "execute" | "compose" | "present"
    applied_assets: Dict[str, str]  # asset_type -> asset_id:version
    params: Dict[str, Any]
    prev_output: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

class StageOutput(BaseModel):
    stage: str
    result: Dict[str, Any]
    diagnostics: StageDiagnostics
    references: List[Dict[str, Any]]
    duration_ms: int

class StageDiagnostics(BaseModel):
    status: str  # "ok" | "warning" | "error"
    warnings: List[str] = []
    errors: List[str] = []
    empty_flags: Dict[str, bool] = {}
    counts: Dict[str, int] = {}
```

### ReplanEvent

```python
class ReplanTrigger(BaseModel):
    trigger_type: str
    reason: str
    severity: str
    stage_name: str

class ReplanPatchDiff(BaseModel):
    before: Dict[str, Any]
    after: Dict[str, Any]

class ReplanEvent(BaseModel):
    event_type: str
    stage_name: str
    trigger: ReplanTrigger
    patch: ReplanPatchDiff
    timestamp: str
    decision_metadata: Dict[str, Any]
```

### ExecutionContext

```python
class ExecutionContext(BaseModel):
    trace_id: str
    test_mode: bool = False
    asset_overrides: Dict[str, str] = {}
    baseline_trace_id: Optional[str] = None
    replan_count: int = 0
    start_time: float = 0.0
    metadata: Dict[str, Any] = {}
```

## Error Handling

All endpoints return a consistent error format:

```json
{
  "code": 400,
  "message": "Bad Request",
  "error": "Detailed error message",
  "details": {}
}
```

Common error codes:
- 400: Bad Request - Invalid request parameters
- 401: Unauthorized - Missing or invalid authentication
- 404: Not Found - Resource not found
- 422: Unprocessable Entity - Validation error
- 500: Internal Server Error - Server-side error

## Rate Limiting

Most endpoints are rate limited to:
- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated users

Rate limit headers in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642675200
```

## Webhooks

The system supports webhook notifications for certain events:

- Trace completion
- Replan events
- Regression analysis results

Subscribe to webhooks via the UI or API endpoint.

## Testing

Use the provided test suite for API validation:

```bash
# Run all tests
pytest tests/ops_e2e/

# Run specific test file
pytest tests/ops_e2e/test_orchestration_e2e.py

# Run with coverage
pytest tests/ops_e2e/ --cov=apps.api
```