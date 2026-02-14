# Exception Handling & Circuit Breaker - Quick Reference

## Quick Start

### 1. Raise an Exception
```python
from app.core.exceptions import ValidationError, CircuitOpenError

# Input validation
raise ValidationError("email", "Invalid email format")  # 400

# Security violation (audit logged)
raise TenantIsolationError("tenant-123", "Access denied")  # 403

# Service unavailable
raise CircuitOpenError("external_api")  # 503
```

### 2. Use Circuit Breaker
```python
from app.llm.circuit_breaker import CircuitBreakerManager

breaker = CircuitBreakerManager.get_or_create("my_service")

try:
    if breaker.is_open():
        raise CircuitOpenError("my_service")

    result = call_service()
    breaker.record_success()
except Exception as e:
    breaker.record_failure()
    raise
```

### 3. Monitor Circuit Breaker
```python
# Get specific breaker stats
stats = breaker.get_stats()
# {
#   "state": "closed",
#   "failure_count": 0,
#   "success_count": 0,
#   ...
# }

# Get all breakers
all_stats = CircuitBreakerManager.get_all_stats()
```

## Exception Reference

| Exception | Code | Status | Use Case |
|-----------|------|--------|----------|
| `AppBaseError` | INTERNAL_ERROR | 500 | Base class (don't raise directly) |
| `ConnectionError` | CONNECTION_ERROR | 503 | DB/service connection failures |
| `TimeoutError` | TIMEOUT | 504 | Operation timeout |
| `ValidationError` | VALIDATION_ERROR | 400 | Input validation |
| `TenantIsolationError` | TENANT_VIOLATION | 403 | Security violation |
| `ToolExecutionError` | TOOL_ERROR | 500 | Tool execution failure |
| `PlanningError` | PLANNING_ERROR | 500 | LLM planning failure |
| `CircuitOpenError` | CIRCUIT_OPEN | 503 | Circuit breaker open |
| `DatabaseError` | DATABASE_ERROR | 503 | Database operation |
| `ExternalServiceError` | EXTERNAL_SERVICE_ERROR | 503 | External service error |
| `RateLimitError` | RATE_LIMIT_EXCEEDED | 429 | Rate limit exceeded |
| `ConfigurationError` | CONFIGURATION_ERROR | 500 | Config error |
| `NotFoundError` | NOT_FOUND | 404 | Resource not found |
| `AuthorizationError` | AUTHORIZATION_ERROR | 403 | Permission denied |
| `ConflictError` | CONFLICT | 409 | Resource conflict |

## Exception Response Format

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Validation failed for email: Invalid email format",
  "status_code": 400,
  "request_id": "req-123456"
}
```

## Circuit Breaker States

```
┌─────────┐
│ CLOSED  │ ← Normal operation (5 failures to trigger)
└────┬────┘
     │ 5 consecutive failures
     ↓
┌─────────┐
│  OPEN   │ ← Fast-fail mode (60s recovery timeout)
└────┬────┘
     │ 60s timeout passes
     ↓
┌───────────┐
│HALF_OPEN  │ ← Recovery mode (2 successes to close)
└──┬─────┬──┘
   │     │
   │ 1   │ 2
   │fail │successes
   ↓     ↓
 OPEN   CLOSED
```

## Configuration

### Circuit Breaker Config
```python
from app.llm.circuit_breaker import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 failures
    recovery_timeout=60.0,      # Try recovery after 60s
    success_threshold=2,        # Close after 2 successes
    expected_exception=Exception
)
```

### LLM Client (Default)
```python
# Automatic in LlmClient.__init__()
CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=2
)
```

## Common Patterns

### Pattern 1: Validate Input
```python
from app.core.exceptions import ValidationError

def process_user(email: str):
    if not is_valid_email(email):
        raise ValidationError("email", "Invalid email format")
    # ... process
```

### Pattern 2: Handle External Service
```python
from app.core.exceptions import ExternalServiceError
from app.llm.circuit_breaker import CircuitBreakerManager

breaker = CircuitBreakerManager.get_or_create("external_api")

def call_external():
    try:
        if breaker.is_open():
            raise ExternalServiceError("external_api", "Circuit breaker open")

        response = requests.get("https://api.example.com/data")
        breaker.record_success()
        return response
    except Exception as e:
        breaker.record_failure()
        raise ExternalServiceError("external_api", str(e))
```

### Pattern 3: Database Operation
```python
from app.core.exceptions import DatabaseError, ConnectionError as AppConnectionError

def query_database(query: str):
    try:
        result = db.execute(query)
        return result
    except ConnectionError as e:
        raise AppConnectionError("postgres", str(e))
    except Exception as e:
        raise DatabaseError(str(e))
```

### Pattern 4: Monitor Health
```python
from app.llm.circuit_breaker import CircuitBreakerManager

@app.get("/health/circuit-breakers")
def health_circuit_breakers():
    stats = CircuitBreakerManager.get_all_stats()

    # Check if any are open
    open_count = sum(1 for s in stats.values() if s["state"] == "open")

    return {
        "status": "degraded" if open_count > 0 else "healthy",
        "open_breakers": open_count,
        "breakers": stats
    }
```

## Logging

### Exception Logging
```
ERROR   - Server errors (500+)
WARNING - Client errors (400s), rate limits (429), timeout (504)
INFO    - Not found (404), expected failures
SECURITY - Tenant violations
```

### Circuit Breaker Logging
```
WARNING - State transitions (CLOSED→OPEN, OPEN→HALF_OPEN, etc.)
INFO    - Recovery attempts in HALF_OPEN state
ERROR   - Fast-fail when circuit is OPEN
```

## Files for Reference

| File | Purpose | Key Classes |
|------|---------|------------|
| `app/core/exceptions.py` | Exception definitions | 14 exception classes |
| `app/core/exception_handlers.py` | Global handlers | `register_exception_handlers()` |
| `app/llm/circuit_breaker.py` | Resilience pattern | `CircuitBreaker`, `CircuitBreakerManager` |
| `app/llm/client.py` | LLM integration | `LlmClient` (modified) |
| `main.py` | App setup | Handler registration |

## Testing

### Import All Components
```python
from app.core.exceptions import AppBaseError, ValidationError
from app.core.exception_handlers import register_exception_handlers
from app.llm.circuit_breaker import CircuitBreaker, CircuitBreakerManager
from app.llm.client import LlmClient
```

### Test Exception
```python
try:
    raise ValidationError("test", "Test error")
except Exception as e:
    assert e.status_code == 400
    assert e.code == "VALIDATION_ERROR"
    assert "Test error" in e.message
```

### Test Circuit Breaker
```python
breaker = CircuitBreaker(
    CircuitBreakerConfig(failure_threshold=2),
    name="test"
)

assert breaker.state.value == "closed"
breaker.record_failure()
breaker.record_failure()
assert breaker.state.value == "open"
assert breaker.is_open() == True
```

## Troubleshooting

### Circuit Breaker Won't Close
- Check: Has 60 seconds passed since it opened?
- Check: Have 2 consecutive successes been recorded?
- Solution: Manually call `breaker.reset()` if needed

### Exception Not Being Caught
- Verify import path: `from app.core.exceptions import ...`
- Check inheritance: Your exception should extend `AppBaseError`
- Verify handler registration: `register_exception_handlers(app)` called

### LLM Client Not Protected
- Verify: Is `_circuit_breaker` attribute present on LlmClient?
- Check: `client._circuit_breaker.state` should be "closed"
- Solution: May need to restart app if modified

## Performance Tips

1. **Reuse Circuit Breakers**: Use `CircuitBreakerManager.get_or_create()`
2. **Set Appropriate Thresholds**: Default 5 failures is usually good
3. **Monitor State Changes**: Enable logging for debugging
4. **Reset Carefully**: Only reset when service is confirmed healthy

## Security Notes

- Tenant violations are specially logged for audit trail
- Never expose sensitive data in error messages
- Use generic messages in production responses
- Request IDs help trace errors through logs
- Circuit breaker prevents cascading failures

## Next Steps

1. Add Prometheus metrics for monitoring
2. Implement retry policies with backoff
3. Add distributed tracing support
4. Create dashboards for circuit breaker state

---

**Version**: 1.0
**Last Updated**: 2026-02-14
**Status**: Production Ready
