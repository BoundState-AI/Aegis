#!/usr/bin/env python3
"""Tests for monitor trigger gate policy."""

from __future__ import annotations

from boundstate_aegis.monitoring.models import ContentDiff
from boundstate_aegis.monitoring.policies import evaluate_trigger


def _diff() -> ContentDiff:
    return ContentDiff(
        diff_id="d1",
        source_id="s1",
        url="https://example.com",
        label="Example",
        country="US",
        diff_type="modified",
        added_word_count=30,
        removed_word_count=25,
        keyword_hits=[],
        noise_filtered=False,
    )


def test_primary_tier_always_triggers_on_substantive_change() -> None:
    decision = evaluate_trigger(diff=_diff(), tier="primary", is_new_url=False)
    assert decision.trigger_level3 is True


def test_keyword_hit_triggers_even_for_small_delta() -> None:
    diff = _diff()
    diff.added_word_count = 10
    diff.removed_word_count = 5
    diff.keyword_hits = ["MCL"]
    decision = evaluate_trigger(diff=diff, tier="secondary", is_new_url=False)
    assert decision.trigger_level3 is True


def test_noise_filtered_does_not_trigger() -> None:
    diff = _diff()
    diff.noise_filtered = True
    decision = evaluate_trigger(diff=diff, tier="primary", is_new_url=False)
    assert decision.trigger_level3 is False
