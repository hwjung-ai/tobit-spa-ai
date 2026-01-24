from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.logging import get_request_context
from sqlalchemy import update
from sqlmodel import Session, select

from app.modules.audit_log.crud import create_audit_log

from .models import TbOperationSettings


def get_setting_by_key(
    session: Session, setting_key: str
) -> TbOperationSettings | None:
    """Get a setting by key."""
    statement = select(TbOperationSettings).where(
        TbOperationSettings.setting_key == setting_key
    )
    return session.exec(statement).first()


def get_all_settings(session: Session) -> list[TbOperationSettings]:
    """Get all settings."""
    statement = select(TbOperationSettings).order_by(TbOperationSettings.setting_key)
    return session.exec(statement).all()


def create_or_update_setting(
    session: Session,
    setting_key: str,
    setting_value: dict[str, Any],
    description: str | None = None,
    published_by: str | None = None,
    restart_required: bool = False,
) -> TbOperationSettings:
    """Create or update a setting."""
    existing = get_setting_by_key(session, setting_key)

    # Get trace info from context
    context = get_request_context()
    trace_id = context.get("trace_id") or str(uuid.uuid4())
    parent_trace_id = context.get("parent_trace_id") or None

    if existing:
        # Store old values for audit
        old_values = {
            "setting_value": existing.setting_value,
            "restart_required": existing.restart_required,
        }

        # Prepare update data
        now = datetime.now(timezone.utc)
        update_values = {
            "setting_value": setting_value,
            "source": "published",
            "restart_required": restart_required,
            "published_by": published_by,
            "published_at": now,
            "updated_at": now,
        }
        if description:
            update_values["description"] = description

        # Execute update
        statement = (
            update(TbOperationSettings)
            .where(TbOperationSettings.setting_id == existing.setting_id)
            .values(**update_values)
        )
        session.execute(statement)
        session.commit()

        # Refresh to get the updated values from DB
        session.refresh(existing)

        # Record audit log
        create_audit_log(
            session=session,
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            resource_type="operation_setting",
            resource_id=existing.setting_key,
            action="update",
            actor=published_by or "system",
            changes={"setting_value": "updated", "restart_required": restart_required},
            old_values=old_values,
            new_values={
                "setting_value": setting_value,
                "restart_required": restart_required,
            },
            metadata={"description": description, "published_by": published_by},
        )

        return existing
    else:
        # Create new setting
        new_setting = TbOperationSettings(
            setting_key=setting_key,
            setting_value=setting_value,
            source="published",
            restart_required=restart_required,
            description=description,
            published_by=published_by,
            published_at=datetime.now(timezone.utc),
        )

        session.add(new_setting)
        session.commit()
        session.refresh(new_setting)

        # Record audit log
        create_audit_log(
            session=session,
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            resource_type="operation_setting",
            resource_id=new_setting.setting_key,
            action="create",
            actor=published_by or "system",
            changes={"setting_key": setting_key, "setting_value": "created"},
            old_values={},
            new_values={
                "setting_value": setting_value,
                "restart_required": restart_required,
            },
            metadata={"description": description, "published_by": published_by},
        )

        return new_setting


def get_setting_effective_value(
    session: Session,
    setting_key: str,
    default_value: Any = None,
    env_value: Any = None,
) -> dict[str, Any]:
    """
    Get the effective value of a setting considering priority:
    published > env > default

    Returns a dict with:
    - value: the effective value
    - source: where the value came from (published/env/default)
    - restart_required: whether a restart is needed
    """
    setting = get_setting_by_key(session, setting_key)

    if setting:
        # Priority: published > env > default
        # If setting exists in published, return that
        # Extract the actual value from the stored JSON object
        actual_value = (
            setting.setting_value.get("value", setting.setting_value)
            if isinstance(setting.setting_value, dict)
            else setting.setting_value
        )
        return {
            "value": actual_value,
            "source": "published",
            "restart_required": setting.restart_required,
        }

    # Fall back to env or default
    if env_value is not None:
        return {
            "value": env_value,
            "source": "env",
            "restart_required": False,
        }

    return {
        "value": default_value,
        "source": "default",
        "restart_required": False,
    }
