from __future__ import annotations

from redis import Redis
from rq import Queue

from core.config import get_settings
from .jobs import parse_and_index_document


def get_rq_queue(name: str = "default") -> Queue:
    settings = get_settings()
    if not settings.redis_url:
        raise ValueError("Redis URL is not configured")
    redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return Queue(name, connection=redis_client)


def enqueue_parse_document(document_id: str):
    queue = get_rq_queue(name="documents")
    return queue.enqueue(parse_and_index_document, document_id=document_id)
