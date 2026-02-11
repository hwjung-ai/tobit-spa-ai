from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from app.modules.auth.models import TbUser
from core.auth import get_current_user
from core.config import get_settings
from core.db import Session, get_session
from core.tenant import get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Query
from models import ChatMessage, ChatThread
from services import (
    BaseOrchestrator,
    ConversationSummaryService,
    get_orchestrator,
    get_summary_service,
)
from sqlmodel import select
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat")

CONTRACT_BY_BUILDER: dict[str, str] = {
    "api-manager": "api_draft",
    "cep-builder": "cep_draft",
    "screen-editor": "screen_patch",
}


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        body = stripped[3:-3]
        lines = body.splitlines()
        if lines and lines[0].strip().lower() in {"json", "javascript", "js"}:
            return "\n".join(lines[1:]).strip()
        return body.strip()
    return text


def _extract_json_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    stack: list[str] = []
    start_idx: int | None = None
    in_string = False
    escaped = False

    for idx, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            if not stack:
                start_idx = idx
            stack.append(ch)
        elif ch in "}]":
            if not stack:
                continue
            opener = stack.pop()
            if (opener == "{" and ch != "}") or (opener == "[" and ch != "]"):
                stack.clear()
                start_idx = None
                continue
            if not stack and start_idx is not None:
                candidates.append(text[start_idx : idx + 1])
                start_idx = None

    return candidates


def _parse_json_candidates(text: str) -> list[Any]:
    parsed: list[Any] = []
    raw_candidates = [_strip_code_fences(text), text]
    for candidate in raw_candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            parsed.append(json.loads(candidate))
        except Exception:
            pass
        for extracted in _extract_json_candidates(candidate):
            try:
                parsed.append(json.loads(extracted))
            except Exception:
                continue
    return parsed


def _validate_contract(expected_contract: str | None, text: str) -> tuple[bool, str | None]:
    if not expected_contract:
        return True, None

    parsed = _parse_json_candidates(text)
    if not parsed:
        return False, "JSON payload를 추출하지 못했습니다."

    if expected_contract == "screen_patch":
        has_patch = any(
            isinstance(value, list)
            or (
                isinstance(value, dict)
                and isinstance(value.get("patch"), list)
            )
            for value in parsed
        )
        if has_patch:
            return True, None
        return False, "JSON Patch 배열 또는 patch 필드가 필요합니다."

    for value in parsed:
        if isinstance(value, dict) and value.get("type") == expected_contract:
            return True, None
    return False, f"type={expected_contract} 객체가 필요합니다."


def _resolve_identity(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> tuple[str, str]:
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return tenant_id, str(current_user.id)


def _derive_title(message: str) -> str:
    snippet = " ".join(message.strip().split())
    return snippet[:30] if snippet else "New conversation"


def _get_or_create_thread(
    session: Session,
    tenant_id: str,
    user_id: str,
    thread_id: str | None,
    message: str,
    builder: str | None = None,
) -> ChatThread:
    if thread_id:
        statement = select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.tenant_id == tenant_id,
            ChatThread.user_id == user_id,
        )
        thread = session.exec(statement).one_or_none()
        if not thread or thread.deleted_at:
            raise HTTPException(status_code=404, detail="Thread not found")
        if builder and not thread.builder:
            thread.builder = builder
            session.add(thread)
            session.commit()
            session.refresh(thread)
        return thread
    title = _derive_title(message)
    thread = ChatThread(
        title=title, tenant_id=tenant_id, user_id=user_id, builder=builder
    )
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
    should_update_title = not thread.title_finalized or thread.title.startswith(
        "New conversation"
    )
    if should_update_title:
        title_source = prompt or content
        thread.title = _derive_title(title_source)
        thread.title_finalized = True
    assistant = ChatMessage(
        thread_id=thread.id, role="assistant", content=content.strip()
    )
    session.add(assistant)
    session.add(thread)
    session.commit()


@router.get("/stream")
async def stream_chat(
    thread_id: str | None = Query(
        None, description="Optional thread id to append the chat"
    ),
    message: str | None = Query(
        None, min_length=1, description="Primary prompt to start the chat"
    ),
    prompt: str | None = Query(
        None,
        min_length=1,
        description="Legacy prompt field; message is preferred",
    ),
    builder: str | None = Query(
        None, description="Optional builder slug to tag the thread"
    ),
    expected_contract: str | None = Query(
        None,
        description="Optional output contract (api_draft|cep_draft|screen_patch)",
    ),
    builder_context: str | None = Query(
        None,
        description="Optional JSON string context for builder-aware prompt",
    ),
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
    orchestrator: BaseOrchestrator = Depends(get_orchestrator),
    summary_service: ConversationSummaryService = Depends(get_summary_service),
) -> EventSourceResponse:
    resolved_message = message or prompt
    if not resolved_message:
        raise HTTPException(status_code=400, detail="message is required")
    if not message and prompt:  # TODO: remove prompt fallback in next release
        message = prompt
    tenant_id, user_id = identity
    thread = _get_or_create_thread(
        session, tenant_id, user_id, thread_id, resolved_message, builder=builder
    )
    _save_user_message(session, thread.id, resolved_message)

    assistant_buffer: list[str] = []
    done_sent = False
    contract_violation_sent = False
    prompt_for_orchestrator = resolved_message

    # 1. Fetch recent messages for context window
    MAX_HISTORY_MESSAGES = 10
    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    past_messages = session.exec(history_stmt).all()
    # Remove the very last user message we just saved, to avoid duplication if it was caught in the query
    # (though typically we want it at the end).
    # Since we just saved it, it should be the most recent one.
    # Let's just re-build the prompt from history + current message carefully.

    # Re-order to chronological
    past_messages = sorted(past_messages, key=lambda m: m.created_at)

    context_str = ""
    for msg in past_messages:
        # Skip the current message if it's already in the DB (which it is, we just saved it)
        # We will append resolved_message explicitly at the end to be safe,
        # or we can just use the history including the current message.
        # Let's use the history excluding the current one to clear confusion, then append current.
        if (
            msg.content == resolved_message
            and msg.role == "user"
            and msg == past_messages[-1]
        ):
            continue
        context_str += f"{msg.role.upper()}: {msg.content}\n"

    if thread.summary:
        logging.info("Thread %s has summary; prepending to prompt", thread.id)
        prompt_for_orchestrator = (
            "Previous conversation summary:\n"
            f"{thread.summary}\n\n"
            "Conversation History:\n"
            f"{context_str}\n"
            f"User asks:\n{resolved_message}"
        )
    elif context_str:
        prompt_for_orchestrator = (
            f"Conversation History:\n{context_str}\nUser asks:\n{resolved_message}"
        )

    # 2. Add builder context for stronger deterministic generation
    if builder_context:
        try:
            context_obj = json.loads(builder_context)
            prompt_for_orchestrator = (
                f"{prompt_for_orchestrator}\n\n"
                "Builder Context (JSON):\n"
                f"{json.dumps(context_obj, ensure_ascii=False)}"
            )
        except Exception:
            logging.warning("Invalid builder_context JSON; ignoring it")

    resolved_contract = expected_contract or (
        CONTRACT_BY_BUILDER.get(builder) if builder else None
    )
    if resolved_contract:
        prompt_for_orchestrator = (
            f"{prompt_for_orchestrator}\n\n"
            f"Output contract must be: {resolved_contract}.\n"
            "Return contract-valid JSON payload only."
        )

    logging.debug(
        "Prompt for thread %s: %s",
        thread.id,
        prompt_for_orchestrator.replace("\n", " ")[:200],
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        nonlocal done_sent, contract_violation_sent
        try:
            async for chunk in orchestrator.stream_chat(prompt_for_orchestrator):
                chunk_type = chunk.get("type")
                if chunk_type == "answer":
                    assistant_buffer.append(chunk.get("text", ""))
                if chunk_type == "done" and not done_sent:
                    assistant_text = "".join(assistant_buffer)
                    contract_ok, reason = _validate_contract(
                        resolved_contract, assistant_text
                    )
                    if not contract_ok and not contract_violation_sent:
                        contract_violation_sent = True
                        yield json.dumps(
                            {
                                "type": "contract_error",
                                "text": reason,
                                "expected_contract": resolved_contract,
                                "thread_id": thread.id,
                            }
                        )
                    _persist_assistant_response(session, thread, assistant_text, resolved_message)
                    summary_service.summarize_thread(session, thread)
                    done_sent = True
                payload = dict(chunk)
                payload["thread_id"] = thread.id
                yield json.dumps(payload)
        except Exception as exc:  # pragma: no cover
            payload = {"type": "error", "text": str(exc), "thread_id": thread.id}
            yield json.dumps(payload)

    return EventSourceResponse(event_generator())
