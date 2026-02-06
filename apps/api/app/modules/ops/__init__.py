"""
OPS Module - Operational Planning and Synthesis

The OPS module provides comprehensive operational planning and execution capabilities
for complex query processing, including planning, validation, execution, and monitoring.

Architecture:
    - routes/: Modularized endpoint handlers organized by functional area
    - services/: Business logic and orchestration
    - schemas.py: Pydantic models for requests/responses
    - errors.py: Custom exception classes
    - error_handler.py: Global exception handlers

Key Features:
    1. CI (Causal Investigation): Plan generation and query understanding
    2. Orchestration: Multi-stage execution with fallback handling
    3. Regression Testing: Golden queries and baseline comparison
    4. RCA (Root Cause Analysis): Trace analysis and diff detection
    5. UI Actions: Deterministic action execution for interactive workflows

Routing:
    - /ops/query: Standard OPS query processing
    - /ops/ci/ask: CI question processing with planning
    - /ops/ui-actions: UI action execution
    - /ops/rca/*: Root cause analysis
    - /ops/golden-queries/*: Golden query management and regression
    - /ops/actions: Recovery action execution
    - /ops/stage-*: Stage testing and comparison

Usage:
    from app.modules.ops import router

    app.include_router(router)
"""

from .error_handler import register_exception_handlers  # noqa: F401
from .routes import get_combined_router

# Create the combined router from modular routes
router = get_combined_router()

__all__ = ["router", "register_exception_handlers"]
