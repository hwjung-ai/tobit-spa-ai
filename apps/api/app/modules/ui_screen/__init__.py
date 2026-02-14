"""UI Screen Module - Screen Editor backend."""

from .models import (
    ScreenCreateRequest,
    ScreenListResponse,
    ScreenPublishRequest,
    ScreenResponse,
    ScreenRollbackRequest,
    ScreenUpdateRequest,
    ScreenVersionResponse,
    TbScreen,
    TbScreenAuditLog,
    TbScreenVersion,
)
from .router import router
from .screen_router import (
    create_screen,
    delete_screen,
    get_screen,
    get_screen_version,
    get_screen_versions,
    list_screens,
    publish_screen,
    rollback_screen,
    unpublish_screen,
    update_screen,
)

__all__ = [
    # Models
    "TbScreen",
    "TbScreenVersion",
    "TbScreenAuditLog",
    # Request/Response
    "ScreenCreateRequest",
    "ScreenUpdateRequest",
    "ScreenPublishRequest",
    "ScreenRollbackRequest",
    "ScreenResponse",
    "ScreenListResponse",
    "ScreenVersionResponse",
    # Router
    "router",
    # CRUD functions
    "create_screen",
    "get_screen",
    "list_screens",
    "update_screen",
    "publish_screen",
    "unpublish_screen",
    "rollback_screen",
    "delete_screen",
    "get_screen_versions",
    "get_screen_version",
]
