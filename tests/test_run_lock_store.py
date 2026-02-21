#!/usr/bin/env python3
"""Tests for monitor run-lock persistence."""

from __future__ import annotations

from pathlib import Path

from boundstate_aegis.monitoring.stores import RunLockStore


def test_run_lock_acquire_release(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "monitor.db"
    monkeypatch.setenv("AEGIS_MONITOR_SQLITE_PATH", str(db_path))
    monkeypatch.delenv("AEGIS_MONITOR_DB_URL", raising=False)

    locks = RunLockStore()
    assert locks.acquire(lock_name="aegis", owner_id="owner-a", ttl_seconds=300) is True
    assert locks.acquire(lock_name="aegis", owner_id="owner-b", ttl_seconds=300) is False

    locks.release(lock_name="aegis", owner_id="owner-a")
    assert locks.acquire(lock_name="aegis", owner_id="owner-b", ttl_seconds=300) is True
