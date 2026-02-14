"""
Screen Editor CRUD Operations
Provides database operations for screen definitions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlmodel import Session, col, select

from .models import (
    ScreenCreateRequest,
    ScreenListResponse,
    ScreenResponse,
    ScreenUpdateRequest,
    ScreenVersionResponse,
    TbScreen,
    TbScreenAuditLog,
    TbScreenVersion,
)

logger = logging.getLogger(__name__)


class ScreenNotFoundError(Exception):
    """Raised when screen is not found."""
    pass


class ScreenVersionConflictError(Exception):
    """Raised when version conflict occurs."""
    pass


def create_screen(
    session: Session,
    tenant_id: str,
    user_id: str,
    request: ScreenCreateRequest,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TbScreen:
    """Create a new screen."""
    screen_id = str(uuid4())
    now = datetime.utcnow()

    screen = TbScreen(
        screen_id=screen_id,
        tenant_id=tenant_id,
        screen_name=request.screen_name,
        screen_type=request.screen_type,
        description=request.description,
        components=request.components,
        layout=request.layout,
        state=request.state,
        bindings=request.bindings,
        actions=request.actions,
        styles=request.styles,
        tags=request.tags,
        meta=request.meta,
        created_by=user_id,
        created_at=now,
        updated_by=user_id,
        updated_at=now,
        version=1,
    )

    session.add(screen)

    # Create initial version
    version = TbScreenVersion(
        version_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        version=1,
        change_summary="Initial version",
        created_by=user_id,
        created_at=now,
        snapshot=screen.model_dump(),
    )
    session.add(version)

    # Create audit log
    audit_log = TbScreenAuditLog(
        log_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        action="create",
        version_from=None,
        version_to=1,
        user_id=user_id,
        timestamp=now,
        details={"screen_name": request.screen_name},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(screen)

    logger.info(f"Created screen {screen_id} for tenant {tenant_id}")
    return screen


def get_screen(
    session: Session,
    screen_id: str,
    tenant_id: str,
) -> TbScreen:
    """Get a screen by ID."""
    statement = select(TbScreen).where(
        TbScreen.screen_id == screen_id,
        TbScreen.tenant_id == tenant_id,
    )
    screen = session.exec(statement).first()

    if not screen:
        raise ScreenNotFoundError(f"Screen {screen_id} not found")

    return screen


def list_screens(
    session: Session,
    tenant_id: str,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    screen_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_published: Optional[bool] = None,
    tags: Optional[List[str]] = None,
) -> ScreenListResponse:
    """List screens with filtering and pagination."""
    offset = (page - 1) * page_size

    # Base query
    statement = select(TbScreen).where(TbScreen.tenant_id == tenant_id)

    # Apply filters
    if search:
        statement = statement.where(
            col(TbScreen.screen_name).icontains(search) |
            col(TbScreen.description).icontains(search)
        )

    if screen_type:
        statement = statement.where(TbScreen.screen_type == screen_type)

    if is_active is not None:
        statement = statement.where(TbScreen.is_active == is_active)

    if is_published is not None:
        statement = statement.where(TbScreen.is_published == is_published)

    if tags:
        # JSON contains check (PostgreSQL specific)
        statement = statement.where(col(TbScreen.tags).contains(tags))

    # Count total
    count_statement = select(TbScreen).where(TbScreen.tenant_id == tenant_id)
    total = len(session.exec(count_statement).all())

    # Order by updated_at desc
    statement = statement.order_by(col(TbScreen.updated_at).desc())
    statement = statement.offset(offset).limit(page_size)

    screens = session.exec(statement).all()

    return ScreenListResponse(
        screens=[ScreenResponse(**s.model_dump()) for s in screens],
        total=total,
        page=page,
        page_size=page_size,
    )


def update_screen(
    session: Session,
    screen_id: str,
    tenant_id: str,
    user_id: str,
    request: ScreenUpdateRequest,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TbScreen:
    """Update an existing screen."""
    screen = get_screen(session, screen_id, tenant_id)
    old_version = screen.version
    now = datetime.utcnow()

    # Update fields
    update_data = request.model_dump(exclude_unset=True, exclude={"change_summary"})
    for key, value in update_data.items():
        if hasattr(screen, key):
            setattr(screen, key, value)

    # Increment version
    screen.version = old_version + 1
    screen.updated_by = user_id
    screen.updated_at = now

    session.add(screen)

    # Create version snapshot
    version = TbScreenVersion(
        version_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        version=screen.version,
        change_summary=request.change_summary or "Updated",
        created_by=user_id,
        created_at=now,
        snapshot=screen.model_dump(),
    )
    session.add(version)

    # Create audit log
    audit_log = TbScreenAuditLog(
        log_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        action="update",
        version_from=old_version,
        version_to=screen.version,
        user_id=user_id,
        timestamp=now,
        details=request.model_dump(exclude_unset=True),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(screen)

    logger.info(f"Updated screen {screen_id} to version {screen.version}")
    return screen


def publish_screen(
    session: Session,
    screen_id: str,
    tenant_id: str,
    user_id: str,
    change_summary: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TbScreen:
    """Publish a screen."""
    screen = get_screen(session, screen_id, tenant_id)
    now = datetime.utcnow()

    screen.is_published = True
    screen.published_at = now
    screen.published_by = user_id
    screen.updated_by = user_id
    screen.updated_at = now

    session.add(screen)

    # Create audit log
    audit_log = TbScreenAuditLog(
        log_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        action="publish",
        version_from=screen.version,
        version_to=screen.version,
        user_id=user_id,
        timestamp=now,
        details={"change_summary": change_summary},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(screen)

    logger.info(f"Published screen {screen_id}")
    return screen


def unpublish_screen(
    session: Session,
    screen_id: str,
    tenant_id: str,
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TbScreen:
    """Unpublish a screen."""
    screen = get_screen(session, screen_id, tenant_id)
    now = datetime.utcnow()

    screen.is_published = False
    screen.updated_by = user_id
    screen.updated_at = now

    session.add(screen)

    # Create audit log
    audit_log = TbScreenAuditLog(
        log_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        action="unpublish",
        version_from=screen.version,
        version_to=screen.version,
        user_id=user_id,
        timestamp=now,
        details={},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(screen)

    logger.info(f"Unpublished screen {screen_id}")
    return screen


def rollback_screen(
    session: Session,
    screen_id: str,
    tenant_id: str,
    user_id: str,
    target_version: int,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TbScreen:
    """Rollback screen to a specific version."""
    screen = get_screen(session, screen_id, tenant_id)
    old_version = screen.version
    now = datetime.utcnow()

    # Get target version snapshot
    version_statement = select(TbScreenVersion).where(
        TbScreenVersion.screen_id == screen_id,
        TbScreenVersion.version == target_version,
    )
    version = session.exec(version_statement).first()

    if not version:
        raise ScreenVersionConflictError(f"Version {target_version} not found")

    # Restore from snapshot
    snapshot = version.snapshot
    for key in ["components", "layout", "state", "bindings", "actions", "styles", "tags", "meta"]:
        if key in snapshot:
            setattr(screen, key, snapshot[key])

    screen.version = old_version + 1  # New version after rollback
    screen.updated_by = user_id
    screen.updated_at = now

    session.add(screen)

    # Create new version for rollback
    new_version = TbScreenVersion(
        version_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        version=screen.version,
        change_summary=f"Rollback to version {target_version}: {reason or 'No reason provided'}",
        created_by=user_id,
        created_at=now,
        snapshot=screen.model_dump(),
    )
    session.add(new_version)

    # Create audit log
    audit_log = TbScreenAuditLog(
        log_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        action="rollback",
        version_from=old_version,
        version_to=screen.version,
        user_id=user_id,
        timestamp=now,
        details={"target_version": target_version, "reason": reason},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit_log)

    session.commit()
    session.refresh(screen)

    logger.info(f"Rolled back screen {screen_id} from v{old_version} to v{target_version}")
    return screen


def delete_screen(
    session: Session,
    screen_id: str,
    tenant_id: str,
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Delete a screen (soft delete by setting is_active=False)."""
    screen = get_screen(session, screen_id, tenant_id)
    now = datetime.utcnow()

    screen.is_active = False
    screen.updated_by = user_id
    screen.updated_at = now

    session.add(screen)

    # Create audit log
    audit_log = TbScreenAuditLog(
        log_id=str(uuid4()),
        screen_id=screen_id,
        tenant_id=tenant_id,
        action="delete",
        version_from=screen.version,
        version_to=screen.version,
        user_id=user_id,
        timestamp=now,
        details={},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit_log)

    session.commit()

    logger.info(f"Deleted screen {screen_id}")


def get_screen_versions(
    session: Session,
    screen_id: str,
    tenant_id: str,
) -> List[ScreenVersionResponse]:
    """Get version history for a screen."""
    # Verify screen exists
    get_screen(session, screen_id, tenant_id)

    statement = (
        select(TbScreenVersion)
        .where(TbScreenVersion.screen_id == screen_id)
        .order_by(col(TbScreenVersion.version).desc())
    )
    versions = session.exec(statement).all()

    return [ScreenVersionResponse(**v.model_dump()) for v in versions]


def get_screen_version(
    session: Session,
    screen_id: str,
    tenant_id: str,
    version: int,
) -> ScreenVersionResponse:
    """Get a specific version of a screen."""
    # Verify screen exists
    get_screen(session, screen_id, tenant_id)

    statement = select(TbScreenVersion).where(
        TbScreenVersion.screen_id == screen_id,
        TbScreenVersion.version == version,
    )
    version_obj = session.exec(statement).first()

    if not version_obj:
        raise ScreenVersionConflictError(f"Version {version} not found")

    return ScreenVersionResponse(**version_obj.model_dump())
