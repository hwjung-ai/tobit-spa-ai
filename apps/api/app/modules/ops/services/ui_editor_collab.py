from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class UIEditorCollabManager:
    """In-memory websocket collaboration manager for UI screen editor."""

    def __init__(self) -> None:
        self._connections: dict[tuple[str, str], dict[WebSocket, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    def _key(self, tenant_id: str, screen_id: str) -> tuple[str, str]:
        return (tenant_id, screen_id)

    def _presence_snapshot_locked(self, key: tuple[str, str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for meta in self._connections.get(key, {}).values():
            rows.append(
                {
                    "session_id": meta["session_id"],
                    "user_id": meta["user_id"],
                    "user_label": meta["user_label"],
                    "updated_at": meta["updated_at"],
                }
            )
        rows.sort(key=lambda item: item["updated_at"], reverse=True)
        return rows

    async def connect(
        self,
        websocket: WebSocket,
        *,
        tenant_id: str,
        screen_id: str,
        session_id: str,
        user_id: str,
        user_label: str,
    ) -> list[dict[str, Any]]:
        await websocket.accept()
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            room = self._connections.setdefault(key, {})
            room[websocket] = {
                "session_id": session_id,
                "user_id": user_id,
                "user_label": user_label,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            snapshot = self._presence_snapshot_locked(key)
        await self.broadcast_presence(tenant_id=tenant_id, screen_id=screen_id)
        return snapshot

    async def disconnect(self, websocket: WebSocket, *, tenant_id: str, screen_id: str) -> None:
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            room = self._connections.get(key)
            if room:
                room.pop(websocket, None)
                if not room:
                    self._connections.pop(key, None)
        await self.broadcast_presence(tenant_id=tenant_id, screen_id=screen_id)

    async def touch(
        self, websocket: WebSocket, *, tenant_id: str, screen_id: str
    ) -> None:
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            room = self._connections.get(key)
            if room and websocket in room:
                room[websocket]["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def broadcast_presence(self, *, tenant_id: str, screen_id: str) -> None:
        key = self._key(tenant_id, screen_id)
        async with self._lock:
            room = dict(self._connections.get(key, {}))
            snapshot = self._presence_snapshot_locked(key)
        if not room:
            return
        payload = {"type": "presence", "sessions": snapshot}
        stale: list[WebSocket] = []
        for ws in room:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                current_room = self._connections.get(key, {})
                for ws in stale:
                    current_room.pop(ws, None)
                if not current_room:
                    self._connections.pop(key, None)

    async def broadcast_screen_update(
        self,
        *,
        tenant_id: str,
        screen_id: str,
        source_session_id: str,
        screen: dict[str, Any],
        updated_at: str | None = None,
    ) -> None:
        key = self._key(tenant_id, screen_id)
        ts = updated_at or datetime.now(timezone.utc).isoformat()
        async with self._lock:
            room = dict(self._connections.get(key, {}))
            for meta in self._connections.get(key, {}).values():
                if meta["session_id"] == source_session_id:
                    meta["updated_at"] = ts
        if not room:
            return
        payload = {
            "type": "screen_update",
            "session_id": source_session_id,
            "screen": screen,
            "updated_at": ts,
        }
        stale: list[WebSocket] = []
        for ws, meta in room.items():
            if meta.get("session_id") == source_session_id:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                current_room = self._connections.get(key, {})
                for ws in stale:
                    current_room.pop(ws, None)
                if not current_room:
                    self._connections.pop(key, None)


ui_editor_collab_manager = UIEditorCollabManager()
