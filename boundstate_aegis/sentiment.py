#!/usr/bin/env python3
"""
Module: sentiment
Purpose: Shared sentiment aggregation utilities for AEGIS SENTINEL.
    Provides category scoring, per-year aggregation, and rolling-window
    normalization used by all compound classification scripts.

    Rev History:
        1.0.0 - Extracted from per-compound scripts; added rolling window

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.6 <noreply@anthropic.com>
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_SCORES: Dict[str, float] = {
    "CELEBRATION": 1.0,
    "UTILITY": 0.5,
    "DETECTION": 0.0,
    "QUESTIONING": -0.5,
    "ALARM": -1.0,
    "RECKONING": -1.0,
}

SENTIMENT_CATEGORIES_META: List[Dict[str, Any]] = [
    {"id": "celebration", "label": "Celebration", "score": 1.0, "color": "#22c55e",
     "description": "Synthesis, novel properties, applications"},
    {"id": "utility", "label": "Methods & Utility", "score": 0.5, "color": "#86efac",
     "description": "Analytical methods, processing techniques"},
    {"id": "detection", "label": "Detection", "score": 0.0, "color": "#eab308",
     "description": "Environmental occurrence, monitoring"},
    {"id": "questioning", "label": "Questioning", "score": -0.5, "color": "#f97316",
     "description": "Persistence, fate, bioaccumulation"},
    {"id": "alarm", "label": "Alarm", "score": -1.0, "color": "#ef4444",
     "description": "Health effects, toxicology, exposure"},
    {"id": "reckoning", "label": "Reckoning", "score": -1.0, "color": "#991b1b",
     "description": "Regulation, remediation, litigation"},
]

DEFAULT_ROLLING_WINDOW = 3  # years


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_sentiment(
    classified: List[Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """Aggregate per-paper classifications into year-by-year sentiment breakdowns."""
    yearly: Dict[int, Dict[str, int]] = {}

    for paper in classified:
        year = paper["year"]
        cat = paper["category"].upper()
        if year not in yearly:
            yearly[year] = {
                "celebration": 0,
                "utility": 0,
                "detection": 0,
                "questioning": 0,
                "alarm": 0,
                "reckoning": 0,
            }
        key = cat.lower()
        if key in yearly[year]:
            yearly[year][key] += 1

    # Compute per-year sentiment scores
    result = {}
    cumulative = 0.0
    for year in sorted(yearly.keys()):
        counts = yearly[year]
        year_score = sum(
            counts[cat.lower()] * score
            for cat, score in CATEGORY_SCORES.items()
        )
        cumulative += year_score
        result[year] = {
            "sentiment": counts,
            "year_sentiment_score": round(year_score, 1),
            "cumulative_sentiment": round(cumulative, 1),
        }

    return result


def compute_rolling_sentiment(
    yearly_sentiment: Dict[int, Dict[str, Any]],
    window: int = DEFAULT_ROLLING_WINDOW,
) -> Dict[int, float]:
    """
    Compute a rolling-window average sentiment score per year.

    For each year, averages the per-year sentiment scores over the
    trailing `window` years (including the current year). This is more
    responsive to real shifts than a cumulative average, which gets
    diluted by decades of prior data.

    Returns {year: rolling_avg} where values are in [-1, +1].
    """
    sorted_years = sorted(yearly_sentiment.keys())
    rolling: Dict[int, float] = {}

    for i, year in enumerate(sorted_years):
        # Gather scores for the trailing window
        start = max(0, i - window + 1)
        window_years = sorted_years[start : i + 1]

        # year_sentiment_score is already the sum of all paper scores for that year.
        # To get weighted average per-paper sentiment across the window:
        #   sum(year_scores) / sum(year_papers)
        total_score = sum(yearly_sentiment[y]["year_sentiment_score"] for y in window_years)
        total_papers = sum(
            sum(yearly_sentiment[y]["sentiment"].values()) for y in window_years
        )

        if total_papers > 0:
            avg = total_score / total_papers
        else:
            avg = 0.0

        # Clamp to [-1, 1]
        rolling[year] = round(max(-1.0, min(1.0, avg)), 3)

    return rolling


def update_backtest_sentiment(
    backtest_path: Path,
    yearly_sentiment: Dict[int, Dict[str, Any]],
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
) -> None:
    """
    Update a backtest JSON file with sentiment data and rolling-window
    normalized sentiment. Shared by all compound classification scripts.
    """
    with open(backtest_path, encoding="utf-8") as f:
        backtest = json.load(f)

    # Compute rolling sentiment
    rolling = compute_rolling_sentiment(yearly_sentiment, window=rolling_window)

    # Update timeline entries
    for entry in backtest["timeline"]:
        year = entry["year"]
        if year in yearly_sentiment:
            entry["sentiment"] = yearly_sentiment[year]["sentiment"]
            entry["cumulative_sentiment"] = yearly_sentiment[year]["cumulative_sentiment"]
            entry["normalized_sentiment"] = rolling.get(year, 0.0)
        else:
            # Pre-publication years: no sentiment data
            entry["sentiment"] = {
                "celebration": 0,
                "utility": 0,
                "detection": 0,
                "questioning": 0,
                "alarm": 0,
                "reckoning": 0,
            }
            entry["cumulative_sentiment"] = 0.0
            entry["normalized_sentiment"] = 0.0

    # Add sentiment category metadata
    backtest["sentiment_categories"] = SENTIMENT_CATEGORIES_META
    backtest["sentiment_window"] = rolling_window

    with open(backtest_path, "w", encoding="utf-8") as f:
        json.dump(backtest, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated {backtest_path} with sentiment data (rolling window={rolling_window})")
