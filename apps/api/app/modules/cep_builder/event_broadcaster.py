from __future__ import annotations

import asyncio
import threading
from typing import Any


class CepEventBroadcaster:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[
            tuple[asyncio.Queue[dict[str, Any]], asyncio.AbstractEventLoop]
        ] = []

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers.append((queue, loop))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers = [
                (item_queue, loop)
                for item_queue, loop in self._subscribers
                if item_queue is not queue
            ]

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        payload = {"type": event_type, "data": data}
        with self._lock:
            subscribers = list(self._subscribers)
        for queue, loop in subscribers:
            try:
                loop.call_soon_threadsafe(_safe_put_nowait, queue, payload)
            except RuntimeError:
                continue


def _safe_put_nowait(
    queue: asyncio.Queue[dict[str, Any]], payload: dict[str, Any]
) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        return


event_broadcaster = CepEventBroadcaster()
