from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache

from app.llm.client import get_llm_client
from core.config import AppSettings, get_settings
from models import ChatMessage, ChatThread
from sqlmodel import Session, select


class ConversationSummaryService:
    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._llm = get_llm_client()
        self._available = bool(settings.openai_api_key)

    def _load_recent_messages(self, session: Session, thread_id: str) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at)
        )
        return session.exec(statement).all()

    def summarize_thread(self, session: Session, thread: ChatThread) -> str | None:
        if not self._available:
            return None
        
        messages = self._load_recent_messages(session, thread.id)
        if not messages:
            return None
            
        # 최근 12개 메시지 추출
        snippet = messages[-12:]
        snippet_text = "\n".join([f"{m.role.title()}: {m.content}" for m in snippet])
        
        try:
            # OpenAI Responses API를 사용하여 직접 요약 (LangChain 의존성 제거)
            input_data = [
                {"role": "system", "content": "You are a helpful assistant that summarizes conversation threads into a single concise sentence or short paragraph."},
                {"role": "user", "content": f"Summarize this conversation concisely:\n\n{snippet_text}"},
            ]
            request_kwargs = {
                "input": input_data,
                "model": self._settings.chat_model,
            }
            if not self._settings.chat_model.startswith("gpt-5"):
                request_kwargs["temperature"] = 0.0
            response = self._llm.create_response(**request_kwargs)
            summary = self._llm.get_output_text(response).strip()
            
        except Exception as exc:  # pragma: no cover
            logging.exception("Failed to summarize thread %s: %s", thread.id, exc)
            return None

        if summary:
            thread.summary = summary
            thread.updated_at = datetime.now(timezone.utc)
            session.add(thread)
            session.commit()
            session.refresh(thread)
            logging.info("Thread %s summary updated: %s", thread.id, summary[:120].replace("\n", " "))
        
        return summary


@lru_cache(maxsize=1)
def get_summary_service() -> ConversationSummaryService:
    return ConversationSummaryService(get_settings())
