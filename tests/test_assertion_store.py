#!/usr/bin/env python3
"""Tests for assertion governance store."""

from __future__ import annotations

from pathlib import Path

import yaml

from boundstate_aegis.monitoring import assertions as assertions_mod
from boundstate_aegis.monitoring.assertions import AssertionStore


def _sample_assertion(assertion_id: str = "TEST_ASSERTION_001") -> dict:
    return {
        "id": assertion_id,
        "assertion": "Sample enforceable assertion",
        "type": "regulatory_enacted",
        "compound_class": "PFAS_class",
        "confidence": 0.95,
        "status": "enforced",
        "dates": {"effective": "2026-01-01"},
        "citations": [],
        "context": ["sample"],
        "threshold_value": "4 ppt",
        "exemptions": [],
    }


def test_assertion_store_upsert_and_history(tmp_path: Path) -> None:
    store = AssertionStore(db_path=tmp_path / "assertions.db")
    decision = store.upsert_assertion(
        payload=_sample_assertion(),
        status="approved",
        region="TEST",
        source_file="test.yaml",
        actor="tester",
        reason="unit test",
        action="approve",
    )
    assert decision.assertion_id == "TEST_ASSERTION_001"
    assert decision.status == "approved"
    assert decision.version == 1
    assert decision.chain_hash

    history = store.list_assertion_history("TEST_ASSERTION_001", limit=10)
    assert history
    assert history[0]["chain_hash"]


def test_assertion_store_validates_required_keys(tmp_path: Path) -> None:
    store = AssertionStore(db_path=tmp_path / "assertions.db")
    bad = {"id": "BROKEN_001"}
    try:
        store.upsert_assertion(
            payload=bad,
            status="approved",
            region="TEST",
            source_file="bad.yaml",
            actor="tester",
            reason="unit test",
            action="approve",
        )
        assert False, "Expected validation failure"
    except ValueError as exc:
        assert "missing required keys" in str(exc).lower()


def test_assertion_store_approve_pending_file(monkeypatch, tmp_path: Path) -> None:
    store = AssertionStore(db_path=tmp_path / "assertions.db")
    monkeypatch.setattr(assertions_mod, "PENDING_ASSERTIONS_DIR", tmp_path / "pending_assertions")
    pending_file = tmp_path / "pending.yaml"
    payload = {"region": "TEST", "assertions": [_sample_assertion("TEST_ASSERTION_002")]}
    pending_file.write_text(yaml.safe_dump(payload), encoding="utf-8")

    decisions = store.approve_pending_file(pending_file, actor="tester", reason="ok")
    assert len(decisions) == 1
    assert decisions[0].assertion_id == "TEST_ASSERTION_002"
