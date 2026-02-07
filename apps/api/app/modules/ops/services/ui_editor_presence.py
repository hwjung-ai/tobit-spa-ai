from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any


class UIEditorPresenceManager:
    """In-memory presence manager for screen editor sessions."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        self._subscribers: dict[
            tuple[str, str], set[asyncio.Queue[dict[str, Any]]]
        ] = {}
        self._lock = asyncio.Lock()
        self._ttl_seconds = 20

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _key(self, tenant_id: str, screen_id: str) -> tuple[str, str]:
        return (tenant_id, screen_id)

    def _session_view(self, session: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "user_label": session["user_label"],
            "tab_name": session.get("tab_name"),
            "last_seen_at": session["last_seen_at"].isoformat(),
        }

    def _snapshot_locked(self, key: tuple[str, str]) -> list[dict[str, Any]]:
        sessions = self._sessions.get(key, {})
        rows = [self._session_view(s) for s in sessions.values()]
        rows.sort(key=lambda item: item["last_seen_at"], reverse=True)
        return rows

    def _prune_locked(self, key: tuple[str, str]) -> None:
        sessions = self._sessions.get(key)
        if not sessions:
            return
        now = self._now()
        stale_ids = []
        for session_id, row in sessions.items():
            seen = row.get("last_seen_at")
            if not isinstance(seen, datetime):
                stale_ids.append(session_id)
                continue
            if (now - seen).total_seconds() > self._ttl_seconds:
                stale_ids.append(session_id)
        for session_id in stale_ids:
            sessions.pop(session_id, None)
        if not sessions:
            self._sessions.pop(key, None)

    async def _broadcast(
        self, key: tuple[str, str], snapshot: list[dict[str, Any]]
    ) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(key, set()))
        if not subscribers:
            return
        payload = {
            "type": "presence",
            "tenant_id": key[0],
            "screen_id": key[1],
            "count": len(snapshot),
            "sessions": snapshot,
        }
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                continue

    async def heartbeat(
        self,
        tenant_id: str,
        screen_id: str,
        session_id: str,
        user_id: str,
        user_label: str,
        tab_name: str | None = None,
    ) -> list[dict[str, Any]]:
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            sessions = self._sessions.setdefault(key, {})
            sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "user_label": user_label,
                "tab_name": tab_name or "",
                "last_seen_at": self._now(),
            }
            self._prune_locked(key)
            snapshot = self._snapshot_locked(key)
        await self._broadcast(key, snapshot)
        return snapshot

    async def leave(
        self, tenant_id: str, screen_id: str, session_id: str
    ) -> list[dict[str, Any]]:
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            sessions = self._sessions.get(key, {})
            sessions.pop(session_id, None)
            if not sessions:
                self._sessions.pop(key, None)
            snapshot = self._snapshot_locked(key)
        await self._broadcast(key, snapshot)
        return snapshot

    async def subscribe(
        self, tenant_id: str, screen_id: str
    ) -> tuple[asyncio.Queue[dict[str, Any]], list[dict[str, Any]]]:
        key = self._key(tenant_id, screen_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=16)
        async with self._lock:
            listeners = self._subscribers.setdefault(key, set())
            listeners.add(queue)
            self._prune_locked(key)
            snapshot = self._snapshot_locked(key)
        return queue, snapshot

    async def unsubscribe(
        self, tenant_id: str, screen_id: str, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            listeners = self._subscribers.get(key)
            if not listeners:
                return
            listeners.discard(queue)
            if not listeners:
                self._subscribers.pop(key, None)


ui_editor_presence_manager = UIEditorPresenceManager()
