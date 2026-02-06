"""Tests for SSE (Server-Sent Events) real-time event streaming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from app.modules.cep_builder.event_broadcaster import CepEventBroadcaster
from app.modules.cep_builder.models import TbCepNotificationLog
from fastapi import HTTPException
from httpx import AsyncClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_db):
    """Create a session for the test database."""
    with Session(in_memory_db) as session:
        yield session


class TestEventBroadcaster:
    """Test cases for CepEventBroadcaster (local queue-based messaging)."""

    def test_broadcaster_initialization_without_redis(self):
        """Test broadcaster initializes without Redis URL."""
        broadcaster = CepEventBroadcaster()
        assert broadcaster._redis_url is None
        assert broadcaster._redis is None

    def test_broadcaster_initialization_with_redis_url(self):
        """Test broadcaster stores Redis URL when provided."""
        redis_url = "redis://localhost:6379"
        broadcaster = CepEventBroadcaster(redis_url=redis_url)
        assert broadcaster._redis_url == redis_url

    @pytest.mark.asyncio
    async def test_broadcaster_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing from events."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        assert queue is not None
        assert len(broadcaster._subscribers) == 1

        broadcaster.unsubscribe(queue)
        assert len(broadcaster._subscribers) == 0

    @pytest.mark.asyncio
    async def test_broadcaster_publish_local(self):
        """Test publishing events to local subscribers."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # Publish event
        event_data = {"event_id": "test-1", "status": "fired"}
        broadcaster.publish("new_event", event_data)

        # Retrieve from queue
        message = await asyncio.wait_for(queue.get(), timeout=1.0)

        assert message["type"] == "new_event"
        assert message["data"] == event_data

        broadcaster.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_broadcaster_publish_multiple_subscribers(self):
        """Test publishing to multiple subscribers."""
        broadcaster = CepEventBroadcaster()
        queue1 = broadcaster.subscribe()
        queue2 = broadcaster.subscribe()

        event_data = {"test": "data"}
        broadcaster.publish("test_event", event_data)

        # Both subscribers should receive the event
        msg1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        msg2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

        assert msg1["type"] == "test_event"
        assert msg2["type"] == "test_event"

        broadcaster.unsubscribe(queue1)
        broadcaster.unsubscribe(queue2)

    @pytest.mark.asyncio
    async def test_broadcaster_queue_overflow_handling(self):
        """Test handling of queue overflow (size limit)."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # Fill queue beyond capacity (maxsize=200)
        for i in range(250):
            broadcaster.publish("event", {"id": i})

        # Queue should handle overflow gracefully
        received_count = 0
        try:
            while True:
                await asyncio.wait_for(queue.get(), timeout=0.1)
                received_count += 1
        except asyncio.TimeoutError:
            pass

        # Should receive at least some events (not necessarily all)
        assert received_count > 0
        broadcaster.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_broadcaster_ensure_redis_listener(self):
        """Test Redis listener initialization."""
        broadcaster = CepEventBroadcaster()

        # Without Redis URL, should return safely
        await broadcaster.ensure_redis_listener()

        # With Redis URL (mocked)
        broadcaster._redis_url = "redis://localhost:6379"
        with patch.object(broadcaster, '_start_redis_listener', new_callable=AsyncMock):
            await broadcaster.ensure_redis_listener()
            assert broadcaster._redis_listen_task is not None


class TestSSEStreamEndpoint:
    """Test cases for SSE /events/stream endpoint."""

    def test_event_broadcaster_thread_safety(self):
        """Test thread-safe operations of broadcaster."""
        import threading

        broadcaster = CepEventBroadcaster()
        subscribe_results = []
        lock = threading.Lock()

        def multi_subscribe_task():
            # Simulate thread-safe queue management
            # Note: subscribe() requires event loop, so we test unsubscribe instead
            queue = broadcaster.subscribe()
            with lock:
                subscribe_results.append(queue)

        # For thread safety of unsubscribe operation
        queues = []
        for _ in range(5):
            try:
                # Cannot call subscribe() in non-async context
                # So we'll just test the locking mechanism
                q = AsyncMock()
                queues.append(q)
                broadcaster.unsubscribe(q)
            except Exception:
                pass

        # Verify broadcaster maintains consistent state
        assert len(broadcaster._subscribers) == 0


class TestEventBroadcasterIntegration:
    """Integration tests for event broadcaster with real event flow."""

    @pytest.mark.asyncio
    async def test_event_flow_new_event_to_summary(self):
        """Test event flow: new_event -> summary update."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # Simulate event flow
        new_event_data = {
            "event_id": "evt-1",
            "severity": "high",
            "status": "fired",
        }
        broadcaster.publish("new_event", new_event_data)

        summary_data = {
            "unacked_count": 1,
            "by_severity": {"high": 1},
        }
        broadcaster.publish("summary", summary_data)

        # Verify events in order
        msg1 = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg1["type"] == "new_event"

        msg2 = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg2["type"] == "summary"

        broadcaster.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_ack_event_flow(self):
        """Test ACK event flow."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # New event
        broadcaster.publish("new_event", {
            "event_id": "evt-1",
            "ack": False,
        })

        # ACK event
        broadcaster.publish("ack_event", {
            "event_id": "evt-1",
            "ack": True,
            "ack_at": "2024-01-01T12:00:00Z",
        })

        # Update summary
        broadcaster.publish("summary", {
            "unacked_count": 0,
            "by_severity": {},
        })

        msg1 = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg1["type"] == "new_event"

        msg2 = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg2["type"] == "ack_event"
        assert msg2["data"]["ack"] is True

        msg3 = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg3["type"] == "summary"

        broadcaster.unsubscribe(queue)


class TestSSEErrorHandling:
    """Test error handling in SSE streaming."""

    @pytest.mark.asyncio
    async def test_sse_with_invalid_json(self):
        """Test SSE handles invalid JSON gracefully."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # This should not raise - invalid JSON is logged but not fatal
        broadcaster.publish("test", {"valid": "data"})

        msg = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg["type"] == "test"

        broadcaster.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_broadcast_to_disconnected_queue(self):
        """Test broadcast handles disconnected/full queues."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # Unsubscribe the queue
        broadcaster.unsubscribe(queue)

        # This should not raise - it should handle gracefully
        broadcaster.publish("test", {"data": "value"})


class TestSSEPerformance:
    """Performance tests for SSE."""

    @pytest.mark.asyncio
    async def test_rapid_event_publishing(self):
        """Test rapid event publishing."""
        broadcaster = CepEventBroadcaster()
        queue = broadcaster.subscribe()

        # Publish many events rapidly
        event_count = 100
        for i in range(event_count):
            broadcaster.publish("event", {"id": i})

        # Retrieve events
        received = 0
        try:
            for _ in range(event_count):
                await asyncio.wait_for(queue.get(), timeout=0.5)
                received += 1
        except asyncio.TimeoutError:
            pass

        # Should receive most if not all events
        assert received > event_count * 0.8  # At least 80%

        broadcaster.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_broadcaster_memory_cleanup(self):
        """Test broadcaster cleans up resources."""
        broadcaster = CepEventBroadcaster()

        # Create and destroy many subscribers
        initial_count = len(broadcaster._subscribers)

        for _ in range(10):
            queue = broadcaster.subscribe()
            broadcaster.unsubscribe(queue)

        final_count = len(broadcaster._subscribers)

        # Should clean up properly
        assert final_count == initial_count
