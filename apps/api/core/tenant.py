"""Tenant utilities for multi-tenancy support."""

from typing import Optional

from fastapi import HTTPException, Request, status

DEFAULT_TENANT_ID = "default"
LEGACY_TENANT_ALIASES = {"t1", "default-tenant"}


def normalize_tenant_id(raw_tenant_id: Optional[str]) -> str:
    """
    Normalize tenant id to single-tenant default value.

    The current deployment is operated in single-tenant mode only.
    Any legacy or unexpected tenant value is normalized to "default".
    """
    tenant = (raw_tenant_id or "").strip()
    if not tenant:
        return DEFAULT_TENANT_ID
    if tenant in LEGACY_TENANT_ALIASES:
        return DEFAULT_TENANT_ID
    if tenant != DEFAULT_TENANT_ID:
        return DEFAULT_TENANT_ID
    return tenant


def get_current_tenant(request: Request) -> str:
    """
    Get the current tenant ID from the request state.

    Args:
        request: FastAPI request object

    Returns:
        Current tenant ID

    Raises:
        HTTPException: If tenant_id is not found in request state
    """
    tenant_id = normalize_tenant_id(getattr(request.state, "tenant_id", None))
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant ID is required"
        )
    return tenant_id


def get_optional_tenant(request: Request) -> Optional[str]:
    """
    Get the current tenant ID from the request state, if available.

    Args:
        request: FastAPI request object

    Returns:
        Current tenant ID or None if not found
    """
    return getattr(request.state, "tenant_id", None)
