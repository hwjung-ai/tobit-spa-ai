"""API Manager versioning endpoints for managing API version history and rollbacks."""

import logging
from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from models.api_definition import ApiAuthMode, ApiDefinition, ApiDefinitionVersion, ApiMode, ApiScope
from schemas import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.auth.models import TbUser

from ..crud import _record_api_version, _api_snapshot, _parse_api_uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])


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


@router.get("/{api_id}/versions", response_model=ResponseEnvelope)
async def get_versions(
    api_id: str,
    session: Session = Depends(get_session),
):
    """Get API version history."""
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        statement = (
            select(ApiDefinitionVersion)
            .where(ApiDefinitionVersion.api_id == api.id)
            .order_by(ApiDefinitionVersion.version.desc())
        )
        rows = session.exec(statement).all()
        current = rows[0].version if rows else None
        versions = [
            {
                "version": row.version,
                "change_type": row.change_type,
                "change_summary": row.change_summary,
                "created_by": row.created_by,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "is_current": row.version == current,
                "snapshot": row.snapshot,
            }
            for row in rows
        ]

        return ResponseEnvelope.success(data={"api_id": api_id, "versions": versions})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get versions failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/rollback", response_model=ResponseEnvelope)
async def rollback_api(
    api_id: str,
    version: Optional[int] = Query(None, description="Target version to rollback to"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Rollback API to a previous version snapshot."""
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        version_statement = (
            select(ApiDefinitionVersion)
            .where(ApiDefinitionVersion.api_id == api.id)
            .order_by(ApiDefinitionVersion.version.desc())
        )
        rows = session.exec(version_statement).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No version history found")

        current_version = rows[0]
        target = None
        if version is not None:
            target = next((row for row in rows if row.version == version), None)
            if not target:
                raise HTTPException(status_code=404, detail=f"Version {version} not found")
        else:
            target = rows[1] if len(rows) > 1 else rows[0]

        snapshot = target.snapshot or {}
        try:
            api.scope = ApiScope(snapshot.get("scope", api.scope.value if hasattr(api.scope, "value") else str(api.scope)))
        except ValueError:
            pass
        api.name = snapshot.get("name", api.name)
        api.method = snapshot.get("method", api.method)
        api.path = snapshot.get("path", api.path)
        api.description = snapshot.get("description")
        api.tags = snapshot.get("tags", api.tags)
        mode_value = snapshot.get("mode")
        if mode_value:
            try:
                api.mode = ApiMode(mode_value)
            except ValueError:
                pass
        api.logic = snapshot.get("logic", api.logic)
        api.runtime_policy = snapshot.get("runtime_policy", api.runtime_policy)
        auth_mode_value = snapshot.get("auth_mode")
        if auth_mode_value:
            api.auth_mode = _parse_auth_mode(str(auth_mode_value))
        api.required_scopes = _normalize_required_scopes(
            snapshot.get("required_scopes", api.required_scopes)
        )
        api.is_enabled = bool(snapshot.get("is_enabled", api.is_enabled))
        api.updated_at = datetime.utcnow()

        session.add(api)
        session.commit()
        session.refresh(api)

        new_version = _record_api_version(
            session,
            api,
            change_type="rollback",
            created_by=getattr(current_user, "id", None),
            change_summary=f"Rolled back from v{current_version.version} to v{target.version}",
        )

        return ResponseEnvelope.success(
            data={
                "api_id": api_id,
                "rolled_back_to_version": target.version,
                "new_version": new_version.version,
                "snapshot": _api_snapshot(api),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
