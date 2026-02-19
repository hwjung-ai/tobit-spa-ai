"""
OPS Routes Package

This package contains modularized routes for the OPS module, organized by functional area.

Routes:
    - query: Standard OPS query processing (@router.post("/query"), @router.get("/observability/kpis"))
    - ask: OPS orchestration with LLM-driven planning (@router.post("/ask"))
    - ui_actions: UI action execution (@router.post("/ui-actions"))
    - rca: Root cause analysis (@router.post("/rca/analyze-trace"), @router.post("/rca/analyze-regression"))
    - regression: Golden queries and regression testing
    - actions: Recovery actions (@router.post("/actions"))
    - threads: Thread management (@router.post("/stage-test"), @router.post("/stage-compare"))
"""

from fastapi import APIRouter

from .actions import router as actions_router
from .ask import router as ask_router
from .ask_stream import router as ask_stream_router
from .query import router as query_router
from .rca import router as rca_router
from .regression import router as regression_router
from .threads import router as threads_router
from .ui_actions import router as ui_actions_router


def get_combined_router() -> APIRouter:
    """Combine all modular routers into a single OPS router.

    Returns:
        APIRouter with all OPS routes registered
    """
    combined = APIRouter(prefix="/ops", tags=["ops"])
    combined.include_router(query_router)
    combined.include_router(ask_router)
    combined.include_router(ask_stream_router)
    combined.include_router(ui_actions_router)
    combined.include_router(rca_router)
    combined.include_router(regression_router)
    combined.include_router(actions_router)
    combined.include_router(threads_router)
    return combined


__all__ = [
    "query_router",
    "ask_router",
    "ui_actions_router",
    "rca_router",
    "regression_router",
    "actions_router",
    "threads_router",
    "get_combined_router",
]
