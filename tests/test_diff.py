#!/usr/bin/env python3
"""Tests for monitor content diff engine."""

from __future__ import annotations

from boundstate_aegis.monitoring.diff import generate_diff
from boundstate_aegis.monitoring.models import ContentSnapshot


def _snapshot(text: str, *, raw_hash: str, content_hash: str) -> ContentSnapshot:
    return ContentSnapshot(
        source_id="src1",
        url="https://example.com",
        label="Example",
        country="US",
        tier="primary",
        raw_hash=raw_hash,
        content_hash=content_hash,
        extracted_text=text,
        captured_at="2026-02-20T00:00:00+00:00",
        content_length=len(text),
        extraction_method="test",
    )


def test_diff_additions_and_removals() -> None:
    previous = _snapshot("One paragraph.\n\nSecond paragraph.", raw_hash="a", content_hash="a")
    current = _snapshot("One paragraph updated.\n\nThird paragraph.", raw_hash="b", content_hash="b")

    diff = generate_diff(previous=previous, current=current, keyword_hits=["MCL"])
    assert diff.diff_type == "modified"
    assert diff.added_word_count > 0
    assert diff.removed_word_count > 0
    assert diff.raw_diff


def test_diff_noise_only_when_normalized_same() -> None:
    previous = _snapshot("Same content", raw_hash="a", content_hash="x")
    current = _snapshot("Same content", raw_hash="b", content_hash="x")
    diff = generate_diff(previous=previous, current=current, keyword_hits=[])
    assert diff.noise_filtered is True
    assert diff.diff_type == "noise_only"
