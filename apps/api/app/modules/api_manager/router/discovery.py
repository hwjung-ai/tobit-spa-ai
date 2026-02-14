"""API Manager discovery endpoints for discovering and registering system APIs."""

import logging
from datetime import datetime

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute
from models.api_definition import ApiDefinition, ApiMode, ApiScope
from schemas import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.auth.models import TbUser

from ..crud import _record_api_version, _api_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])


@router.get("/system/endpoints", response_model=ResponseEnvelope)
async def list_discovered_endpoints(request: Request):
    """Discover all API endpoints from the current FastAPI app."""
    try:
        openapi = request.app.openapi() or {}
        paths = openapi.get("paths") or {}
        if not isinstance(paths, dict):
            paths = {}

        discovered: dict[tuple[str, str], dict] = {}
        for path, operations in paths.items():
            if not isinstance(operations, dict):
                continue
            for method, operation in operations.items():
                method_upper = str(method).upper()
                if method_upper in {"HEAD", "OPTIONS"}:
                    continue
                if not isinstance(operation, dict):
                    continue
                discovered[(method_upper, path)] = {
                    "method": method_upper,
                    "path": path,
                    "operationId": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "description": operation.get("description"),
                    "tags": operation.get("tags") or [],
                    "parameters": operation.get("parameters") or [],
                    "requestBody": operation.get("requestBody"),
                    "responses": operation.get("responses") or {},
                    "source": "openapi",
                }

        if not discovered:
            for route in request.app.routes:
                if not isinstance(route, APIRoute):
                    continue
                methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
                for method in methods:
                    discovered[(method, route.path)] = {
                        "method": method,
                        "path": route.path,
                        "operationId": route.operation_id,
                        "summary": route.summary,
                        "description": route.description,
                        "tags": route.tags or [],
                        "parameters": [],
                        "requestBody": None,
                        "responses": {},
                        "source": "router",
                    }

        endpoints = [
            discovered[key]
            for key in sorted(discovered.keys(), key=lambda item: (item[1], item[0]))
        ]
        return ResponseEnvelope.success(
            data={"endpoints": endpoints, "count": len(endpoints)}
        )
    except Exception as e:
        logger.error(f"Discover endpoints failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/system/endpoints/register", response_model=ResponseEnvelope)
async def register_discovered_endpoints(
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Discover FastAPI endpoints and upsert them as system APIs."""
    try:
        discovery_response = await list_discovered_endpoints(request)
        discovered = (
            (discovery_response.data or {}).get("endpoints", [])
            if hasattr(discovery_response, "data")
            else []
        )
        created = 0
        updated = 0
        skipped = 0
        for endpoint in discovered:
            path = endpoint.get("path")
            method = str(endpoint.get("method") or "").upper()
            if not path or not method:
                skipped += 1
                continue
            existing = session.exec(
                select(ApiDefinition)
                .where(ApiDefinition.path == path)
                .where(ApiDefinition.method == method)
                .where(ApiDefinition.deleted_at.is_(None))
                .limit(1)
            ).first()
            if existing:
                existing.scope = ApiScope.system
                existing.name = existing.name or endpoint.get("operationId") or f"{method} {path}"
                existing.description = existing.description or endpoint.get("summary")
                existing.tags = endpoint.get("tags") or existing.tags or []
                existing.runtime_policy = existing.runtime_policy or {}
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                updated += 1
                continue
            api = ApiDefinition(
                scope=ApiScope.system,
                name=endpoint.get("operationId") or endpoint.get("summary") or f"{method} {path}",
                method=method,
                path=path,
                description=endpoint.get("summary") or endpoint.get("description"),
                tags=endpoint.get("tags") or [],
                mode=ApiMode.http,
                logic='{"method":"GET","url":"http://127.0.0.1:8000/health"}',
                is_enabled=True,
            )
            session.add(api)
            session.flush()
            _record_api_version(
                session,
                api,
                change_type="create",
                created_by=getattr(current_user, "id", None),
                change_summary="Auto-registered from OpenAPI discovery",
            )
            created += 1
        session.commit()
        return ResponseEnvelope.success(
            data={
                "discovered": len(discovered),
                "created": created,
                "updated": updated,
                "skipped": skipped,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register discovered endpoints failed: {str(e)}")
        raise HTTPException(500, str(e))
