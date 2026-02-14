"""Router modules for CEP Builder - combines all sub-routers."""

from fastapi import APIRouter

from .channels import router as channels_router
from .events import router as events_router
from .notifications import router as notifications_router
from .performance import router as performance_router
from .rules import router as rules_router
from .scheduler import router as scheduler_router
from .simulation import router as simulation_router

# Main combined router
# Sub-routers already include `/cep/...` prefixes. Keep this router prefix-less
# to avoid duplicated paths such as `/cep/cep/events/...`.
router = APIRouter(tags=["cep-builder"])

# Include all sub-routers
router.include_router(rules_router)
router.include_router(notifications_router)
router.include_router(events_router)
router.include_router(scheduler_router)
router.include_router(performance_router)
router.include_router(simulation_router)
router.include_router(channels_router)

__all__ = ["router"]
