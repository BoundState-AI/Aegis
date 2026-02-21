#!/usr/bin/env python3
"""Generate synthetic triage examples from assertion corpora."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from boundstate_aegis.config import APAC_REGULATORY_ASSERTIONS, WESTERN_REGULATORY_ASSERTIONS


def _load_assertions(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    rows = payload.get("assertions", [])
    return [row for row in rows if isinstance(row, dict)]


def _severity_for_confidence(confidence: float) -> str:
    if confidence >= 0.95:
        return "high"
    if confidence >= 0.85:
        return "medium"
    return "low"


def build_examples() -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    for path in (APAC_REGULATORY_ASSERTIONS, WESTERN_REGULATORY_ASSERTIONS):
        for row in _load_assertions(path):
            text = str(row.get("assertion") or "").strip()
            if not text:
                continue
            confidence = float(row.get("confidence", 0.0) or 0.0)
            classification = str(row.get("type", "data_update")).replace("regulatory_", "regulatory_")
            compounds = []
            if row.get("compound_class"):
                compounds.append(str(row["compound_class"]))
            example = {
                "assertion_id": row.get("id"),
                "source_file": path.name,
                "diff": {
                    "added_lines": [text],
                    "removed_lines": [],
                    "keyword_hits": [],
                },
                "expected_classification": classification,
                "expected_severity": _severity_for_confidence(confidence),
                "expected_compounds": compounds,
            }
            examples.append(example)
    return examples


def main() -> None:
    out = build_examples()
    print(json.dumps({"total": len(out), "examples": out}, indent=2))


if __name__ == "__main__":
    main()

