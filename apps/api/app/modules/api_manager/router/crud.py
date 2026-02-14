"""API Manager CRUD endpoints for creating, reading, and updating API definitions."""

import logging
import uuid
from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from models.api_definition import ApiAuthMode, ApiDefinition, ApiMode, ApiScope
from pydantic import BaseModel, Field
from schemas import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.auth.models import TbUser

from ..crud import _record_api_version, _api_snapshot, _parse_api_uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])


class CreateApiRequest(BaseModel):
    """Request to create new API"""

    name: str
    method: str
    path: str
    mode: str  # sql, python, workflow
    logic: str
    scope: str = "custom"
    input_schema: dict = {}
    output_schema: dict = {}
    description: Optional[str] = None
    auth_mode: str = ApiAuthMode.jwt_only.value
    required_scopes: list[str] = []


class UpdateApiRequest(BaseModel):
    """Request to update API"""

    name: Optional[str] = None
    logic: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    description: Optional[str] = None
    auth_mode: Optional[str] = None
    required_scopes: Optional[list[str]] = None


class SaveApiRequest(BaseModel):
    """Request to save/create API from frontend"""

    api_name: str
    api_type: str  # "system" or "custom"
    method: str
    endpoint: str
    description: Optional[str] = None
    tags: list[str] = []
    logic_type: str  # "sql", "python", "workflow", "script", "http"
    logic_body: str
    param_schema: dict = {}
    runtime_policy: dict = {}
    logic_spec: dict = {}
    is_active: bool = True
    created_by: Optional[str] = None
    auth_mode: str = ApiAuthMode.jwt_only.value
    required_scopes: list[str] = []


class UpdateApiAuthPolicyRequest(BaseModel):
    auth_mode: str = ApiAuthMode.jwt_only.value
    required_scopes: list[str] = []


def _parse_auth_mode(mode: str | None) -> ApiAuthMode:
    if not mode:
        return ApiAuthMode.jwt_only
    try:
        return ApiAuthMode(mode)
    except ValueError:
        return ApiAuthMode.jwt_only


def _normalize_required_scopes(scopes: list[str] | None) -> list[str]:
    if not scopes:
        return []
    normalized: list[str] = []
    for scope in scopes:
        text = str(scope).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


@router.get("/apis", response_model=ResponseEnvelope)
async def list_apis(
    scope: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """List all available APIs. Tenant-isolated."""

    try:
        tenant_id = getattr(current_user, "tenant_id", None)
        statement = select(ApiDefinition).where(ApiDefinition.deleted_at.is_(None))

        # Tenant isolation
        if tenant_id:
            statement = statement.where(
                (ApiDefinition.tenant_id == tenant_id) | (ApiDefinition.tenant_id.is_(None))
            )

        if scope:
            try:
                scope_enum = ApiScope(scope)
                statement = statement.where(ApiDefinition.scope == scope_enum)
            except ValueError:
                pass

        apis = session.exec(statement).all()

        api_list = [
            {
                "id": str(api.id),
                "scope": api.scope.value,
                "name": api.name,
                "method": api.method,
                "path": api.path,
                "description": api.description,
                "tags": api.tags or [],
                "mode": api.mode.value if api.mode else None,
                "logic": api.logic,
                "runtime_policy": api.runtime_policy or {},
                "auth_mode": (
                    api.auth_mode.value if hasattr(api.auth_mode, "value") else str(api.auth_mode)
                ),
                "required_scopes": list(api.required_scopes or []),
                "is_enabled": api.is_enabled,
                "created_at": api.created_at.isoformat() if api.created_at else None,
                "updated_at": api.updated_at.isoformat() if api.updated_at else None,
            }
            for api in apis
        ]

        return ResponseEnvelope.success(data={"apis": api_list})

    except Exception as e:
        logger.error(f"List APIs failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/apis", response_model=ResponseEnvelope)
async def create_or_update_api(
    request: SaveApiRequest,
    api_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Create or update API definition"""
    try:
        # Map frontend field names to backend field names
        api_scope = (
            ApiScope(request.api_type)
            if request.api_type in ["system", "custom"]
            else ApiScope.custom
        )
        api_mode = (
            ApiMode(request.logic_type)
            if request.logic_type in [m.value for m in ApiMode]
            else ApiMode.sql
        )
        auth_mode = _parse_auth_mode(request.auth_mode)
        required_scopes = _normalize_required_scopes(request.required_scopes)

        if api_id:
            # Update existing API
            api = session.get(ApiDefinition, _parse_api_uuid(api_id))
            if not api or api.deleted_at:
                raise HTTPException(status_code=404, detail="API not found")

            api.name = request.api_name
            api.method = request.method.upper()
            api.path = request.endpoint
            api.description = request.description
            api.tags = request.tags
            api.mode = api_mode
            api.logic = (
                request.logic_body
                if request.logic_type == "sql"
                else request.logic_body
            )
            api.runtime_policy = request.runtime_policy or {}
            if api_mode in {ApiMode.script, ApiMode.python} and "allow_runtime" not in api.runtime_policy:
                api.runtime_policy = {**api.runtime_policy, "allow_runtime": True}
            api.auth_mode = auth_mode
            api.required_scopes = required_scopes
            api.updated_at = datetime.utcnow()
        else:
            # Create new API
            runtime_policy = request.runtime_policy or {}
            if api_mode in {ApiMode.script, ApiMode.python} and "allow_runtime" not in runtime_policy:
                runtime_policy = {**runtime_policy, "allow_runtime": True}
            api = ApiDefinition(
                scope=api_scope,
                name=request.api_name,
                method=request.method.upper(),
                path=request.endpoint,
                description=request.description,
                tags=request.tags,
                mode=api_mode,
                logic=request.logic_body,
                runtime_policy=runtime_policy,
                auth_mode=auth_mode,
                required_scopes=required_scopes,
                is_enabled=request.is_active,
            )
            session.add(api)

        session.commit()
        session.refresh(api)
        _record_api_version(
            session,
            api,
            change_type="update" if api_id else "create",
            created_by=getattr(current_user, "id", None),
            change_summary="Saved from /api-manager/apis",
        )

        return ResponseEnvelope.success(data={
            "api": {
                "id": str(api.id),
                "scope": api.scope.value,
                "name": api.name,
                "method": api.method,
                "path": api.path,
                "description": api.description,
                "tags": api.tags or [],
                "mode": api.mode.value if api.mode else None,
                "logic": api.logic,
                "runtime_policy": api.runtime_policy or {},
                "auth_mode": (
                    api.auth_mode.value if hasattr(api.auth_mode, "value") else str(api.auth_mode)
                ),
                "required_scopes": list(api.required_scopes or []),
                "is_enabled": api.is_enabled,
                "created_at": api.created_at.isoformat()
                if api.created_at
                else None,
                "updated_at": api.updated_at.isoformat()
                if api.updated_at
                else None,
            }
        })
    except Exception as e:
        logger.error(f"Create/update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/create", response_model=ResponseEnvelope)
async def create_api(
    request: CreateApiRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Create new dynamic API (legacy endpoint).
    Prefer POST /apis for new integrations.
    """
    try:
        api_scope = (
            ApiScope(request.scope)
            if request.scope in [s.value for s in ApiScope]
            else ApiScope.custom
        )
        api_mode = (
            ApiMode(request.mode)
            if request.mode in [m.value for m in ApiMode]
            else ApiMode.sql
        )
        auth_mode = _parse_auth_mode(request.auth_mode)
        required_scopes = _normalize_required_scopes(request.required_scopes)

        api = ApiDefinition(
            scope=api_scope,
            name=request.name,
            method=request.method.upper(),
            path=request.path,
            description=request.description,
            mode=api_mode,
            logic=request.logic,
            runtime_policy=(
                {"allow_runtime": True} if api_mode in {ApiMode.script, ApiMode.python} else {}
            ),
            auth_mode=auth_mode,
            required_scopes=required_scopes,
            is_enabled=True,
        )
        session.add(api)
        session.commit()
        session.refresh(api)
        _record_api_version(
            session,
            api,
            change_type="create",
            created_by=getattr(current_user, "id", None),
            change_summary="Created from legacy /api-manager/create",
        )

        return ResponseEnvelope.success(data={
            "id": str(api.id),
            "scope": api.scope.value,
            "name": api.name,
            "method": api.method,
            "path": api.path,
            "mode": api.mode.value if api.mode else None,
            "logic": api.logic,
            "runtime_policy": api.runtime_policy or {},
            "auth_mode": (
                api.auth_mode.value if hasattr(api.auth_mode, "value") else str(api.auth_mode)
            ),
            "required_scopes": list(api.required_scopes or []),
            "is_enabled": api.is_enabled,
            "version": 1,
        })

    except Exception as e:
        logger.error(f"Create API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}", response_model=ResponseEnvelope)
async def get_api(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Get API definition by ID. Tenant-isolated."""
    try:
        tenant_id = getattr(current_user, "tenant_id", None)
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Check tenant access
        if tenant_id and api.tenant_id and api.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="API not found")

        return ResponseEnvelope.success(data={
            "id": str(api.id),
            "scope": api.scope.value,
            "name": api.name,
            "method": api.method,
            "path": api.path,
            "description": api.description,
            "tags": api.tags or [],
            "mode": api.mode.value if api.mode else None,
            "logic": api.logic,
            "runtime_policy": api.runtime_policy or {},
            "auth_mode": (
                api.auth_mode.value if hasattr(api.auth_mode, "value") else str(api.auth_mode)
            ),
            "required_scopes": list(api.required_scopes or []),
            "is_enabled": api.is_enabled,
            "created_at": api.created_at.isoformat() if api.created_at else None,
            "updated_at": api.updated_at.isoformat() if api.updated_at else None,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.put("/apis/{api_id}", response_model=ResponseEnvelope)
async def update_api(
    api_id: str,
    request: SaveApiRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Update API definition
    """

    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Map frontend field names to backend field names
        api_mode = (
            ApiMode(request.logic_type)
            if request.logic_type in [m.value for m in ApiMode]
            else ApiMode.sql
        )

        # Update fields
        api.name = request.api_name
        api.method = request.method.upper()
        api.path = request.endpoint
        api.description = request.description
        api.tags = request.tags
        api.mode = api_mode
        api.logic = request.logic_body
        api.runtime_policy = request.runtime_policy or {}
        if api_mode in {ApiMode.script, ApiMode.python} and "allow_runtime" not in api.runtime_policy:
            api.runtime_policy = {**api.runtime_policy, "allow_runtime": True}
        api.auth_mode = _parse_auth_mode(request.auth_mode)
        api.required_scopes = _normalize_required_scopes(request.required_scopes)
        api.is_enabled = request.is_active
        api.updated_at = datetime.utcnow()

        session.add(api)
        session.commit()
        session.refresh(api)
        _record_api_version(
            session,
            api,
            change_type="update",
            created_by=getattr(current_user, "id", None),
            change_summary="Updated from PUT /api-manager/apis/{api_id}",
        )

        return ResponseEnvelope.success(data={
            "api": {
                "id": str(api.id),
                "scope": api.scope.value,
                "name": api.name,
                "method": api.method,
                "path": api.path,
                "description": api.description,
                "tags": api.tags or [],
                "mode": api.mode.value if api.mode else None,
                "logic": api.logic,
                "runtime_policy": api.runtime_policy or {},
                "auth_mode": (
                    api.auth_mode.value if hasattr(api.auth_mode, "value") else str(api.auth_mode)
                ),
                "required_scopes": list(api.required_scopes or []),
                "is_enabled": api.is_enabled,
                "created_at": api.created_at.isoformat()
                if api.created_at
                else None,
                "updated_at": api.updated_at.isoformat()
                if api.updated_at
                else None,
            }
        })

    except Exception as e:
        logger.error(f"Update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.put("/apis/{api_id}/auth-policy", response_model=ResponseEnvelope)
async def update_api_auth_policy(
    api_id: str,
    request: UpdateApiAuthPolicyRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Update only authentication policy for an API definition."""
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        api.auth_mode = _parse_auth_mode(request.auth_mode)
        api.required_scopes = _normalize_required_scopes(request.required_scopes)
        api.updated_at = datetime.utcnow()

        session.add(api)
        session.commit()
        session.refresh(api)
        _record_api_version(
            session,
            api,
            change_type="update",
            created_by=getattr(current_user, "id", None),
            change_summary="Updated auth policy from /api-manager/apis/{api_id}/auth-policy",
        )

        return ResponseEnvelope.success(
            data={
                "api_id": str(api.id),
                "auth_mode": (
                    api.auth_mode.value if hasattr(api.auth_mode, "value") else str(api.auth_mode)
                ),
                "required_scopes": list(api.required_scopes or []),
                "updated_at": api.updated_at.isoformat() if api.updated_at else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update API auth policy failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/apis/{api_id}", response_model=ResponseEnvelope)
async def delete_api(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Delete API (soft delete)"""

    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Soft delete - mark deleted_at timestamp
        api.deleted_at = datetime.utcnow()
        session.add(api)
        session.commit()

        return ResponseEnvelope.success(message=f"API {api_id} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))
