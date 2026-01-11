from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator, Optional, Tuple

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from sqlmodel import select

from core.db import Session, get_session
from models import ChatMessage, ChatThread
from services import (
    BaseOrchestrator,
    ConversationSummaryService,
    get_orchestrator,
    get_summary_service,
)

router = APIRouter(prefix="/chat")


def _resolve_identity(
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Tuple[str, str]:
    return tenant_id or "default", user_id or "default"


def _derive_title(message: str) -> str:
    snippet = " ".join(message.strip().split())
    return snippet[:30] if snippet else "New conversation"


def _get_or_create_thread(
    session: Session, tenant_id: str, user_id: str, thread_id: Optional[str], message: str
) -> ChatThread:
    if thread_id:
        statement = select(ChatThread).where(ChatThread.id == thread_id)
        thread = session.exec(statement).one_or_none()
        if not thread or thread.deleted_at:
            raise HTTPException(status_code=404, detail="Thread not found")
        return thread
    title = _derive_title(message)
    thread = ChatThread(title=title, tenant_id=tenant_id, user_id=user_id)
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return thread


def _save_user_message(session: Session, thread_id: str, text: str) -> ChatMessage:
    message = ChatMessage(thread_id=thread_id, role="user", content=text)
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def _persist_assistant_response(
    session: Session, thread: ChatThread, content: str, prompt: str | None = None
) -> None:
    if not content.strip():
        return
    thread.updated_at = datetime.now(timezone.utc)
    should_update_title = (
        not thread.title_finalized
        or thread.title.startswith("New conversation")
    )
    if should_update_title:
        title_source = prompt or content
        thread.title = _derive_title(title_source)
        thread.title_finalized = True
    assistant = ChatMessage(thread_id=thread.id, role="assistant", content=content.strip())
    session.add(assistant)
    session.add(thread)
    session.commit()


@router.get("/stream")
async def stream_chat(
    thread_id: str | None = Query(None, description="Optional thread id to append the chat"),
    message: str | None = Query(None, min_length=1, description="Primary prompt to start the chat"),
    prompt: str | None = Query(
        None,
        min_length=1,
        description="Legacy prompt field; message is preferred",
    ),
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
    orchestrator: BaseOrchestrator = Depends(get_orchestrator),
    summary_service: ConversationSummaryService = Depends(get_summary_service),
) -> EventSourceResponse:
    resolved_message = message or prompt
    if not resolved_message:
        raise HTTPException(status_code=400, detail="message is required")
    if not message and prompt:  # TODO: remove prompt fallback in next release
        message = prompt
    tenant_id, user_id = identity
    thread = _get_or_create_thread(session, tenant_id, user_id, thread_id, resolved_message)
    _save_user_message(session, thread.id, resolved_message)

    assistant_buffer: list[str] = []
    done_sent = False
    prompt_for_orchestrator = resolved_message
    if thread.summary:
        logging.info("Thread %s has summary; prepending to prompt", thread.id)
        prompt_for_orchestrator = (
            "Previous conversation summary:\n"
            f"{thread.summary}\n\n"
            f"User asks:\n{resolved_message}"
        )
        logging.debug(
            "Prompt for thread %s: %s",
            thread.id,
            prompt_for_orchestrator.replace("\n", " ")[:200],
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        nonlocal done_sent
        try:
            async for chunk in orchestrator.stream_chat(prompt_for_orchestrator):
                chunk_type = chunk.get("type")
                if chunk_type == "answer":
                    assistant_buffer.append(chunk.get("text", ""))
                if chunk_type == "done" and not done_sent:
                    _persist_assistant_response(
                        session, thread, "".join(assistant_buffer), resolved_message
                    )
                    summary_service.summarize_thread(session, thread)
                    done_sent = True
                payload = dict(chunk)
                payload["thread_id"] = thread.id
                yield json.dumps(payload)
        except Exception as exc:  # pragma: no cover
            payload = {"type": "error", "text": str(exc), "thread_id": thread.id}
            yield json.dumps(payload)

    return EventSourceResponse(event_generator())
