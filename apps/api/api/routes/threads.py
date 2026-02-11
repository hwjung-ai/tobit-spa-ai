from datetime import datetime

from app.modules.auth.models import TbUser
from core.auth import get_current_user
from core.config import get_settings
from core.db import Session, get_session
from core.tenant import get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.chat import ChatMessage, ChatThread
from schemas.thread import ThreadCreate, ThreadDetail, ThreadRead
from sqlmodel import select

router = APIRouter(prefix="/threads", tags=["threads"])


def _resolve_identity(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> tuple[str, str]:
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return tenant_id, str(current_user.id)


@router.post("/", response_model=ThreadRead, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ThreadCreate,
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> ThreadRead:
    tenant_id, user_id = identity
    title = payload.title or "New conversation"
    thread = ChatThread(
        title=title, tenant_id=tenant_id, user_id=user_id, builder=payload.builder
    )
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return thread


@router.get("/", response_model=list[ThreadRead])
def list_threads(
    builder: str | None = Query(None, description="Filter threads by builder slug"),
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> list[ThreadRead]:
    tenant_id, user_id = identity
    statement = select(ChatThread).where(
        ChatThread.deleted_at.is_(None),
        ChatThread.tenant_id == tenant_id,
        ChatThread.user_id == user_id,
    )
    if builder:
        statement = statement.where(ChatThread.builder == builder)
    else:
        statement = statement.where(ChatThread.builder.is_(None))

    statement = statement.order_by(ChatThread.updated_at.desc())
    threads = session.exec(statement).all()
    return [ThreadRead.model_validate(thread.model_dump()) for thread in threads]


@router.get("/{thread_id}", response_model=ThreadDetail)
def get_thread(
    thread_id: str,
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> ThreadDetail:
    tenant_id, user_id = identity
    thread = session.exec(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.tenant_id == tenant_id,
            ChatThread.user_id == user_id,
        )
    ).one_or_none()
    if not thread or thread.deleted_at:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages_stmt = (
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at)
    )
    messages = session.exec(messages_stmt).all()
    thread_data = thread.model_dump()
    thread_data["messages"] = [message.model_dump() for message in messages]
    return ThreadDetail(**thread_data)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    thread_id: str,
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> None:
    tenant_id, user_id = identity
    thread = session.exec(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.tenant_id == tenant_id,
            ChatThread.user_id == user_id,
        )
    ).one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.deleted_at = datetime.utcnow()
    session.add(thread)
    session.commit()
