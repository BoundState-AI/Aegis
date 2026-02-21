#!/usr/bin/env python3
"""
Module: regulatory_coverage_audit
Purpose: Production quality audit for regulatory intelligence coverage.
    Compares monitored jurisdictions (L1 URL monitor) against imported
    regulatory rule datasets (framework + APAC assertions) and reports gaps.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

import yaml

from boundstate_aegis.config import (
    APAC_REGULATORY_ASSERTIONS,
    REGULATORY_FRAMEWORK_YAML,
    WESTERN_REGULATORY_ASSERTIONS,
)
from boundstate_aegis.monitoring.url_monitor import ALL_URLS


APAC_COUNTRY_MAP = {
    "JPN": "Japan",
    "KOR": "South Korea",
    "CHN": "China",
    "AUS": "Australia",
    "SGP": "Singapore",
    "TWN": "Taiwan",
    "IND": "India",
    "APAC": "APAC",
}

WESTERN_COUNTRY_MAP = {
    "US": "United States",
    "EU": "European Union",
    "UK": "United Kingdom",
    "DNK": "Denmark",
    "NOR": "Norway",
    "DEU": "Germany",
    "SWE": "Sweden",
    "NLD": "Netherlands",
    "CAN": "Canada",
    "INTL": "International",
}


def _canonical_country(value: str) -> str:
    token = (value or "").strip()
    if not token:
        return "Unknown"
    upper = token.upper()
    if upper.startswith("US"):
        return "United States"
    if upper in {"UK", "UNITED KINGDOM"}:
        return "United Kingdom"
    if upper == "EU":
        return "European Union"
    if upper == "INTERNATIONAL":
        return "International"
    if upper == "APAC":
        return "APAC"
    return token


def _canonical_framework_jurisdiction(value: str) -> str:
    base = (value or "").split("(", 1)[0].strip()
    if base in {"California", "North Carolina", "Michigan"}:
        return "United States"
    return _canonical_country(base)


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _monitored_jurisdictions() -> List[str]:
    countries = {_canonical_country(entry.country) for entry in ALL_URLS}
    return sorted(countries)


def _framework_jurisdictions(framework: Dict[str, Any]) -> Set[str]:
    jurisdictions: Set[str] = set()
    for entries in framework.get("regulatory_framework", {}).values():
        for entry in entries or []:
            jurisdictions.add(_canonical_framework_jurisdiction(entry.get("jurisdiction", "")))
    return jurisdictions


def _apac_assertion_countries(apac_data: Dict[str, Any]) -> Set[str]:
    countries: Set[str] = set()
    for assertion in apac_data.get("assertions", []):
        prefix = (assertion.get("id", "").split("_", 1)[0] or "APAC").upper()
        countries.add(_canonical_country(APAC_COUNTRY_MAP.get(prefix, "APAC")))
    return countries


def _western_assertion_countries(western_data: Dict[str, Any]) -> Set[str]:
    countries: Set[str] = set()
    for assertion in western_data.get("assertions", []):
        prefix = (assertion.get("id", "").split("_", 1)[0] or "INTL").upper()
        countries.add(_canonical_country(WESTERN_COUNTRY_MAP.get(prefix, prefix)))
    return countries


def _confidence_bands(confidences: Iterable[float]) -> Dict[str, int]:
    bands = Counter()
    for c in confidences:
        if c >= 0.95:
            bands[">=0.95"] += 1
        elif c >= 0.85:
            bands["0.85-0.94"] += 1
        elif c >= 0.75:
            bands["0.75-0.84"] += 1
        elif c >= 0.60:
            bands["0.60-0.74"] += 1
        else:
            bands["<0.60"] += 1
    return dict(bands)


def _is_covered_by_regional_proxy(country: str, represented: Set[str]) -> bool:
    if country in {"Denmark", "Germany", "Netherlands", "Norway", "Sweden"}:
        return "European Union" in represented
    if country == "New Zealand":
        return "International" in represented
    if country == "Brazil":
        return "International" in represented
    return False


def build_audit() -> Dict[str, Any]:
    apac_data = _load_yaml(APAC_REGULATORY_ASSERTIONS)
    western_data = _load_yaml(WESTERN_REGULATORY_ASSERTIONS)
    framework_data = _load_yaml(REGULATORY_FRAMEWORK_YAML)

    monitored = _monitored_jurisdictions()
    framework_jurisdictions = _framework_jurisdictions(framework_data)
    apac_countries = _apac_assertion_countries(apac_data)
    western_countries = _western_assertion_countries(western_data)
    represented = framework_jurisdictions | apac_countries | western_countries

    uncovered: List[str] = []
    for country in monitored:
        if country in represented:
            continue
        if _is_covered_by_regional_proxy(country, represented):
            continue
        uncovered.append(country)

    assertions = apac_data.get("assertions", [])
    confidences = [float(a.get("confidence", 0.0) or 0.0) for a in assertions]
    status_counts = Counter((a.get("status") or "unknown").lower() for a in assertions)
    low_conf_ids = [a.get("id", "") for a in assertions if float(a.get("confidence", 0.0) or 0.0) < 0.85]
    unverified_ids = [a.get("id", "") for a in assertions if (a.get("status") or "").lower() == "unverified"]
    secondary_only_ids = [
        a.get("id", "")
        for a in assertions
        if (a.get("citations") or [])
        and all((c.get("tier", "secondary") == "secondary") for c in (a.get("citations") or []))
    ]

    western_assertions = western_data.get("assertions", [])
    western_confidences = [float(a.get("confidence", 0.0) or 0.0) for a in western_assertions]
    western_status_counts = Counter((a.get("status") or "unknown").lower() for a in western_assertions)
    western_low_conf_ids = [
        a.get("id", "") for a in western_assertions if float(a.get("confidence", 0.0) or 0.0) < 0.85
    ]

    return {
        "monitor": {
            "total_urls": len(ALL_URLS),
            "jurisdictions": monitored,
            "jurisdiction_count": len(monitored),
        },
        "imported_rules": {
            "framework_compound_count": len(framework_data.get("regulatory_framework", {})),
            "framework_jurisdictions": sorted(framework_jurisdictions),
            "apac_assertion_count": len(assertions),
            "apac_coverage": apac_data.get("coverage", []),
            "apac_assertion_countries": sorted(apac_countries),
            "western_assertion_count": len(western_assertions),
            "western_coverage": western_data.get("coverage", []),
            "western_assertion_countries": sorted(western_countries),
        },
        "gaps": {
            "uncovered_monitored_jurisdictions": sorted(uncovered),
            "missing_count": len(uncovered),
        },
        "quality": {
            "apac_status_counts": dict(status_counts),
            "apac_confidence_bands": _confidence_bands(confidences),
            "apac_low_confidence_ids": low_conf_ids,
            "apac_unverified_ids": unverified_ids,
            "apac_secondary_only_ids": secondary_only_ids,
            "western_status_counts": dict(western_status_counts),
            "western_confidence_bands": _confidence_bands(western_confidences),
            "western_low_confidence_ids": western_low_conf_ids,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS regulatory coverage quality audit")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file path to write JSON audit report.",
    )
    args = parser.parse_args()

    report = build_audit()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
