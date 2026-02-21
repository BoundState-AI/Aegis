#!/usr/bin/env python3
"""Tests for Chemours source-priority classification."""

from __future__ import annotations

from boundstate_aegis.monitoring.source_policy import (
    RunProfile,
    classify_source,
    select_sources,
)
from boundstate_aegis.monitoring.url_monitor import ALL_URLS


def test_apac_primary_sources_are_critical() -> None:
    for entry in ALL_URLS:
        tier = getattr(entry.tier, "value", str(entry.tier))
        if entry.country in {"Japan", "South Korea", "China", "Australia", "India", "Singapore", "Taiwan"} and tier in {"primary", "document"}:
            cls = classify_source(entry)
            assert cls.priority == "critical"


def test_priority_profile_excludes_sweep() -> None:
    selected = select_sources(ALL_URLS, profile=RunProfile.PRIORITY.value)
    for entry in selected:
        assert classify_source(entry).priority in {"critical", "active"}


def test_sweep_profile_only_sweep() -> None:
    selected = select_sources(ALL_URLS, profile=RunProfile.SWEEP.value)
    assert selected
    for entry in selected:
        assert classify_source(entry).priority == "sweep"


def test_active_profile_only_active() -> None:
    selected = select_sources(ALL_URLS, profile=RunProfile.ACTIVE.value)
    assert selected
    for entry in selected:
        assert classify_source(entry).priority == "active"
