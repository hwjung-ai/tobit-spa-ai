import asyncio

import pytest

from app.modules.ops.services.ui_editor_presence import UIEditorPresenceManager


@pytest.mark.asyncio
async def test_presence_heartbeat_and_leave() -> None:
    manager = UIEditorPresenceManager()

    snapshot = await manager.heartbeat(
        tenant_id="t1",
        screen_id="screen_a",
        session_id="s1",
        user_id="u1",
        user_label="user1",
        tab_name="visual",
    )
    assert len(snapshot) == 1
    assert snapshot[0]["session_id"] == "s1"

    snapshot = await manager.leave("t1", "screen_a", "s1")
    assert snapshot == []


@pytest.mark.asyncio
async def test_presence_subscribe_receives_broadcast() -> None:
    manager = UIEditorPresenceManager()
    queue, initial = await manager.subscribe("t1", "screen_b")
    assert initial == []

    await manager.heartbeat(
        tenant_id="t1",
        screen_id="screen_b",
        session_id="s2",
        user_id="u2",
        user_label="user2",
        tab_name="preview",
    )
    payload = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert payload["type"] == "presence"
    assert payload["count"] == 1
    assert payload["sessions"][0]["session_id"] == "s2"

    await manager.unsubscribe("t1", "screen_b", queue)
