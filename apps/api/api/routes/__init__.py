from app.modules.api_manager.router import router as api_manager_router
from .cep_builder import router as cep_builder_router
from .chat import router as chat_router
from .documents import router as document_router
from .health import router as health_router
from .hello import router as hello_router
from .ops import router as ops_router
from .threads import router as thread_router

__all__ = [
    "health_router",
    "hello_router",
    "chat_router",
    "thread_router",
    "document_router",
    "ops_router",
    "api_manager_router",
    "cep_builder_router",
]
