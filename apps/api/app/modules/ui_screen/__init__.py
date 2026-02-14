"""UI Screen Module - Screen Editor backend."""

from .models import (
    TbScreen,
    TbScreenVersion,
    TbScreenAuditLog,
    ScreenCreateRequest,
    ScreenUpdateRequest,
    ScreenPublishRequest,
    ScreenRollbackRequest,
    ScreenResponse,
    ScreenListResponse,
    ScreenVersionResponse,
)
from .router import router
from .screen_router import (
    create_screen,
    get_screen,
    list_screens,
    update_screen,
    publish_screen,
    unpublish_screen,
    rollback_screen,
    delete_screen,
    get_screen_versions,
    get_screen_version,
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
