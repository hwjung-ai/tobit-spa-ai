import httpx

try:
    from httpx import AsyncClient as _AsyncClient
    from httpx._transports.asgi import ASGITransport

    class TestAsyncClient(_AsyncClient):
        def __init__(self, *args, app=None, **kwargs):
            if app is not None:
                kwargs.setdefault("transport", ASGITransport(app=app))
            super().__init__(*args, **kwargs)

    httpx.AsyncClient = TestAsyncClient  # type: ignore[attr-defined]
except ImportError:
    pass

from .routes.chat import router as chat_router
from .routes.health import router as health_router
from .routes.hello import router as hello_router

__all__ = ["health_router", "hello_router", "chat_router"]
