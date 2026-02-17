from __future__ import annotations

import main
import pytest


class _DummyTask:
    def cancel(self) -> None:
        return None

    def done(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_on_startup_runs_migrations_before_deferred_heavy_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main, "_should_defer_heavy_startup", lambda: True)
    monkeypatch.setattr(main, "_run_migrations", lambda _logger: calls.append("migrate"))

    def _fake_create_task(coro):
        calls.append("create_task")
        coro.close()
        return _DummyTask()

    monkeypatch.setattr(main.asyncio, "create_task", _fake_create_task)

    await main.on_startup()

    assert calls == ["migrate", "create_task"]


@pytest.mark.asyncio
async def test_on_startup_runs_migrations_before_sync_heavy_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main, "_should_defer_heavy_startup", lambda: False)
    monkeypatch.setattr(main, "_run_migrations", lambda _logger: calls.append("migrate"))

    async def _fake_run_heavy_startup(_logger) -> None:
        calls.append("heavy")

    monkeypatch.setattr(main, "_run_heavy_startup", _fake_run_heavy_startup)

    await main.on_startup()

    assert calls == ["migrate", "heavy"]
