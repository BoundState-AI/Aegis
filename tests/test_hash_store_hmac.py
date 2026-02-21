#!/usr/bin/env python3
"""Tests for hash-store HMAC integrity enforcement."""

from __future__ import annotations

import json
from pathlib import Path

from boundstate_aegis.monitoring import url_monitor


def _record(url: str) -> url_monitor.URLHashRecord:
    return url_monitor.URLHashRecord(
        url=url,
        hash="abc123",
        last_checked="2026-02-21T00:00:00+00:00",
        last_changed="2026-02-21T00:00:00+00:00",
        status="ok",
        content_length=123,
        check_count=1,
        change_count=0,
    )


def test_hash_store_hmac_roundtrip(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(url_monitor, "HASH_STORE_DIR", tmp_path)
    monkeypatch.setattr(url_monitor, "HASH_STORE_FILE", tmp_path / "url_hashes.json")
    monkeypatch.setattr(url_monitor, "HASH_STORE_SECRET", "secret")

    store = {"https://example.com": _record("https://example.com")}
    url_monitor.save_hash_store(store)
    loaded = url_monitor.load_hash_store()
    assert "https://example.com" in loaded


def test_hash_store_hmac_detects_tampering(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(url_monitor, "HASH_STORE_DIR", tmp_path)
    monkeypatch.setattr(url_monitor, "HASH_STORE_FILE", tmp_path / "url_hashes.json")
    monkeypatch.setattr(url_monitor, "HASH_STORE_SECRET", "secret")

    store = {"https://example.com": _record("https://example.com")}
    url_monitor.save_hash_store(store)

    payload = json.loads((tmp_path / "url_hashes.json").read_text(encoding="utf-8"))
    payload["data"]["https://example.com"]["hash"] = "tampered"
    (tmp_path / "url_hashes.json").write_text(json.dumps(payload), encoding="utf-8")

    try:
        url_monitor.load_hash_store()
        assert False, "Expected HMAC mismatch to raise"
    except RuntimeError as exc:
        assert "hmac" in str(exc).lower()
