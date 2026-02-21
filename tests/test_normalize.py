#!/usr/bin/env python3
"""Tests for monitor text normalization."""

from __future__ import annotations

from boundstate_aegis.monitoring.normalize import content_hash, normalize_text


def test_normalize_removes_noise_lines() -> None:
    raw = """
    Skip to main content
    Last updated: 2026-02-20
    New PFAS compliance deadline is 2027-04-13.
    Privacy policy
    """
    normalized, rules = normalize_text(raw)
    assert "Skip to main content" not in normalized
    assert "Last updated" not in normalized
    assert "Privacy policy" not in normalized
    assert "2027-04-13" in normalized
    assert "collapse_whitespace" in rules


def test_normalize_hash_stable_for_equivalent_whitespace() -> None:
    a, _ = normalize_text("A  B   C")
    b, _ = normalize_text("A B C")
    assert content_hash(a) == content_hash(b)
