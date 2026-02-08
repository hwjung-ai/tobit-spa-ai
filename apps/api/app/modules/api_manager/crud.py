from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from models import ApiExecutionLog
from sqlalchemy import text
from sqlmodel import Session, select

from .models import ApiExecLog, ApiExecStepLog, TbApiDef
from .schemas import ApiDefinitionCreate, ApiDefinitionUpdate, ApiType

VALID_LOGIC_TYPES = {"sql", "workflow", "python", "script", "http"}
DRY_RUN_API_ID = "00000000-0000-0000-0000-000000000000"


def _table_exists(session: Session, table_name: str) -> bool:
    result = session.exec(
        text("SELECT to_regclass(:table_name)"),
        params={"table_name": f"public.{table_name}"},
    ).one()
    return bool(result[0])


def list_api_definitions(
    session: Session, api_type: ApiType | None = None
) -> list[TbApiDef]:
    statement = select(TbApiDef)
    if api_type:
        statement = statement.where(TbApiDef.api_type == api_type)
    statement = statement.order_by(TbApiDef.updated_at.desc())
    return session.exec(statement).all()


def get_api_definition(session: Session, api_id: str) -> TbApiDef | None:
    return session.get(TbApiDef, api_id)


def create_api_definition(session: Session, payload: ApiDefinitionCreate) -> TbApiDef:
    if payload.logic_type not in VALID_LOGIC_TYPES:
        raise ValueError("Unsupported logic_type")
    obj = TbApiDef(
        api_name=payload.api_name,
        api_type=payload.api_type,
        method=payload.method.upper(),
        endpoint=payload.endpoint,
        logic_type=payload.logic_type,
        logic_body=payload.logic_body,
        description=payload.description,
        tags=payload.tags,
        param_schema=payload.param_schema,
        runtime_policy=payload.runtime_policy,
        logic_spec=payload.logic_spec,
        is_active=payload.is_active,
        created_by=payload.created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_api_definition(
    session: Session, api: TbApiDef, updates: ApiDefinitionUpdate
) -> TbApiDef:
    data = updates.model_dump(exclude_none=True)
    if not data:
        return api
    if "logic_type" in data and data["logic_type"] not in VALID_LOGIC_TYPES:
        raise ValueError("Unsupported logic_type")
    if "method" in data:
        data["method"] = data["method"].upper()
    for key, value in data.items():
        setattr(api, key, value)
    api.updated_at = datetime.utcnow()
    session.add(api)
    session.commit()
    session.refresh(api)
    return api


def record_exec_log(
    session: Session,
    api_id: str,
    status: str,
    duration_ms: int,
    row_count: int,
    params: dict[str, Any],
    executed_by: str | None,
    error_message: str | None = None,
) -> ApiExecLog | ApiExecutionLog | None:
    api_id_str = str(api_id)
    if api_id_str == DRY_RUN_API_ID:
        return None
    api_uuid = uuid.UUID(api_id_str)
    if _table_exists(session, "tb_api_exec_log"):
        log = ApiExecLog(
            api_id=api_uuid,
            executed_by=executed_by,
            status=status,
            duration_ms=duration_ms,
            row_count=row_count,
            request_params=params or None,
            error_message=error_message,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log

    if _table_exists(session, "api_execution_logs"):
        log = ApiExecutionLog(
            api_id=api_uuid,
            executed_by=executed_by,
            duration_ms=duration_ms,
            request_params=params or None,
            response_status=status,
            error_message=error_message,
            rows_affected=row_count,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log

    return None


def record_exec_step(
    session: Session,
    exec_id: str | uuid.UUID | None,
    node_id: str,
    node_type: str,
    status: str,
    duration_ms: int,
    row_count: int,
    references: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> ApiExecStepLog | None:
    if not exec_id:
        return None
    if not _table_exists(session, "tb_api_exec_step_log"):
        return None
    exec_uuid = uuid.UUID(str(exec_id))
    step = ApiExecStepLog(
        exec_id=exec_uuid,
        node_id=node_id,
        node_type=node_type,
        status=status,
        duration_ms=duration_ms,
        row_count=row_count,
        references=references,
        error_message=error_message,
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def list_exec_logs(
    session: Session, api_id: str, limit: int = 50
) -> list[ApiExecLog | ApiExecutionLog]:
    api_uuid = uuid.UUID(api_id)
    if _table_exists(session, "tb_api_exec_log"):
        statement = (
            select(ApiExecLog)
            .where(ApiExecLog.api_id == api_uuid)
            .order_by(ApiExecLog.executed_at.desc())
            .limit(limit)
        )
        return session.exec(statement).all()
    if _table_exists(session, "api_execution_logs"):
        statement = (
            select(ApiExecutionLog)
            .where(ApiExecutionLog.api_id == api_uuid)
            .order_by(ApiExecutionLog.execution_time.desc())
            .limit(limit)
        )
        return session.exec(statement).all()
    return []
