"""API Manager router - combines all focused sub-routers into a unified API."""

from fastapi import APIRouter

# Import executor functions for backward compatibility
from ..executor import execute_http_api, execute_sql_api, is_http_logic_body
from ..script_executor import execute_script_api
from ..workflow_executor import execute_workflow_api
from .crud import (
    CreateApiRequest,
    SaveApiRequest,
    UpdateApiAuthPolicyRequest,
    UpdateApiRequest,
    create_api,
    create_or_update_api,
    delete_api,
    get_api,
    list_apis,
    update_api,
    update_api_auth_policy,
)
from .crud import router as crud_router
from .discovery import list_discovered_endpoints, register_discovered_endpoints
from .discovery import router as discovery_router
from .execution import (
    ExecuteApiRequest,
    dry_run,
    execute_api,
    run_tests,
    validate_sql,
)
from .execution import router as execution_router
from .export import (
    ExportApiToToolsRequest,
    export_api_to_tools,
    get_api_export_options,
    unlink_api_from_tool,
)
from .export import router as export_router
from .logs import get_logs
from .logs import router as logs_router
from .versioning import get_versions, rollback_api
from .versioning import router as versioning_router

# Main router that combines all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(discovery_router)
router.include_router(crud_router)
router.include_router(versioning_router)
router.include_router(execution_router)
router.include_router(export_router)
router.include_router(logs_router)

__all__ = [
    # Router
    "router",
    # Sub-routers
    "crud_router",
    "discovery_router",
    "versioning_router",
    "execution_router",
    "export_router",
    "logs_router",
    # CRUD endpoints
    "list_apis",
    "create_api",
    "create_or_update_api",
    "get_api",
    "update_api",
    "update_api_auth_policy",
    "delete_api",
    # Discovery endpoints
    "list_discovered_endpoints",
    "register_discovered_endpoints",
    # Versioning endpoints
    "get_versions",
    "rollback_api",
    # Execution endpoints
    "validate_sql",
    "execute_api",
    "run_tests",
    "dry_run",
    # Executor functions (for backward compatibility)
    "execute_sql_api",
    "execute_http_api",
    "execute_script_api",
    "execute_workflow_api",
    "is_http_logic_body",
    # Export endpoints
    "get_api_export_options",
    "export_api_to_tools",
    "unlink_api_from_tool",
    # Logs endpoints
    "get_logs",
    # Request models
    "CreateApiRequest",
    "SaveApiRequest",
    "UpdateApiRequest",
    "UpdateApiAuthPolicyRequest",
    "ExecuteApiRequest",
    "ExportApiToToolsRequest",
]
