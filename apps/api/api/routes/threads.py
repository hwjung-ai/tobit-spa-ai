from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select

from core.db import Session, get_session
from models.chat import ChatMessage, ChatThread
from schemas.thread import MessageRead, ThreadCreate, ThreadDetail, ThreadRead

router = APIRouter(prefix="/threads", tags=["threads"])


def _resolve_identity(
    tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
    user_id: str | None = Header(None, alias="X-User-Id"),
) -> tuple[str, str]:
    return tenant_id or "default", user_id or "default"


@router.post("/", response_model=ThreadRead, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ThreadCreate,
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> ThreadRead:
    tenant_id, user_id = identity
    title = payload.title or "New conversation"
    thread = ChatThread(title=title, tenant_id=tenant_id, user_id=user_id, builder=payload.builder)
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return thread


@router.get("/", response_model=list[ThreadRead])
def list_threads(
    builder: str | None = Query(None, description="Filter threads by builder slug"),
    session: Session = Depends(get_session),
) -> list[ThreadRead]:
    statement = select(ChatThread).where(ChatThread.deleted_at.is_(None))
    if builder:
        statement = statement.where(ChatThread.builder == builder)
    else:
        statement = statement.where(ChatThread.builder.is_(None))

    statement = statement.order_by(ChatThread.updated_at.desc())
    threads = session.exec(statement).scalars().all()
    return [ThreadRead.model_validate(thread.model_dump()) for thread in threads]


@router.get("/{thread_id}", response_model=ThreadDetail)
def get_thread(
    thread_id: str, session: Session = Depends(get_session)
) -> ThreadDetail:
    thread = session.get(ChatThread, thread_id)
    if not thread or thread.deleted_at:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages_stmt = select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(
        ChatMessage.created_at
    )
    messages = session.exec(messages_stmt).scalars().all()
    thread_data = thread.model_dump()
    thread_data["messages"] = [message.model_dump() for message in messages]
    return ThreadDetail(**thread_data)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    thread_id: str, session: Session = Depends(get_session)
) -> None:
    thread = session.get(ChatThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.deleted_at = datetime.utcnow()
    session.add(thread)
    session.commit()
