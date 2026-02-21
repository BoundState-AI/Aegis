#!/usr/bin/env python3
"""Simple precision/recall evaluation harness for triage outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def evaluate(gold_set: List[Dict[str, Any]], predictions: List[Dict[str, Any]]) -> Dict[str, float]:
    by_id = {row["id"]: row for row in predictions if "id" in row}
    tp = fp = fn = 0
    for row in gold_set:
        rid = row.get("id")
        expected = row.get("expected_classification")
        got = (by_id.get(rid) or {}).get("classification")
        if got == expected:
            tp += 1
        elif got is None:
            fn += 1
        else:
            fp += 1
            fn += 1
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return {"precision": round(precision, 4), "recall": round(recall, 4)}


def main() -> None:
    gold_path = Path("monitor_data/training/gold_set.json")
    pred_path = Path("monitor_data/training/predictions.json")
    if not gold_path.exists() or not pred_path.exists():
        print(
            json.dumps(
                {
                    "error": "Missing input files",
                    "required": [str(gold_path), str(pred_path)],
                },
                indent=2,
            )
        )
        return
    gold_set = json.loads(gold_path.read_text(encoding="utf-8"))
    predictions = json.loads(pred_path.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(gold_set, predictions), indent=2))


if __name__ == "__main__":
    main()

