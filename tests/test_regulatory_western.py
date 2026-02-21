#!/usr/bin/env python3
"""Validation tests for Western regulatory assertions dataset."""

from __future__ import annotations

from pathlib import Path

import yaml

from boundstate_aegis.config import APAC_REGULATORY_ASSERTIONS, WESTERN_REGULATORY_ASSERTIONS


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def test_western_file_exists() -> None:
    assert WESTERN_REGULATORY_ASSERTIONS.exists()


def test_western_schema_matches_apac_required_keys() -> None:
    apac = _load_yaml(APAC_REGULATORY_ASSERTIONS)
    western = _load_yaml(WESTERN_REGULATORY_ASSERTIONS)

    apac_assertions = apac.get("assertions", [])
    western_assertions = western.get("assertions", [])
    assert apac_assertions
    assert western_assertions

    required_keys = set(apac_assertions[0].keys())
    for assertion in western_assertions:
        assert required_keys.issubset(assertion.keys()), assertion.get("id")


def test_western_minimum_coverage_and_ids() -> None:
    western = _load_yaml(WESTERN_REGULATORY_ASSERTIONS)
    assertions = western.get("assertions", [])
    assertion_ids = {a.get("id") for a in assertions}

    assert len(assertions) >= 35
    assert "US_EPA_NPDWR_2024_001" in assertion_ids
    assert "US_EPA_NPDWR_2025_001" in assertion_ids
    assert "EU_ECHA_PFAS_001" in assertion_ids


def test_western_epa_discontinuity_is_explicit() -> None:
    western = _load_yaml(WESTERN_REGULATORY_ASSERTIONS)
    by_id = {a["id"]: a for a in western.get("assertions", []) if a.get("id")}

    rule_2024 = by_id["US_EPA_NPDWR_2024_001"]
    rule_2025 = by_id["US_EPA_NPDWR_2025_001"]

    assert rule_2024["status"] == "enforced"
    assert rule_2024["dates"]["effective"] == "2024-06-25"

    assert rule_2025["status"] == "proposed"
    assert rule_2025["dates"]["proposed"] == "2025-05-14"
    assert "reconsider" in rule_2025["assertion"].lower() or "resc" in rule_2025["assertion"].lower()


def test_echa_rac_status_not_mislabeled_finalized() -> None:
    western = _load_yaml(WESTERN_REGULATORY_ASSERTIONS)
    by_id = {a["id"]: a for a in western.get("assertions", []) if a.get("id")}
    rac = by_id["EU_ECHA_RAC_STATUS_001"]
    assert rac["status"] in {"consultation", "proposed", "monitoring"}


def test_mandatory_fixes_persist() -> None:
    western = _load_yaml(WESTERN_REGULATORY_ASSERTIONS)
    by_id = {a["id"]: a for a in western.get("assertions", []) if a.get("id")}

    # 1) CERCLA has a proposal date.
    assert by_id["US_EPA_CERCLA_001"]["dates"]["proposed"] == "2022-09-06"

    # 2) SVHC PFOA has temporal anchors.
    svhc_dates = by_id["EU_SVHC_PFOA_001"]["dates"]
    assert svhc_dates["effective"] == "2013-06-20"
    assert svhc_dates["finalized"] == "2013-06-20"

    # 3) Nordic assertions are thresholded, not placeholders.
    for assertion_id in ("NOR_PFAS_RESTRICTION_001", "DEU_UBA_PFAS_001", "SWE_KEMI_PFAS_001"):
        threshold = by_id[assertion_id]["threshold_value"]
        assert isinstance(threshold, str) and threshold.strip()

    # 4) CompTox baseline count is populated.
    assert by_id["US_EPA_COMPTOX_001"]["compounds_covered"] >= 14000

    # 5) RAC status is not finalized.
    assert by_id["EU_ECHA_RAC_STATUS_001"]["status"] != "finalized"
