#!/usr/bin/env python3
"""
Module: sentinel_route
Purpose: AEGIS SENTINEL — Litigation Early Warning System.
    Serves historical backtest data proving publication dynamics
    as leading indicators of PFAS litigation.

    The GenX case study reconstructs what SENTINEL would have shown
    had it been active during the GenX/HFPO-DA contamination timeline
    (2006-2025), demonstrating a 2-year lead time before the first lawsuit.

    Rev History:
        1.0.0 - Initial SENTINEL routes with GenX backtest

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from boundstate_aegis.config import EVIDENCE_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

GENX_BACKTEST_PATH = EVIDENCE_DIR / "genx_backtest.json"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TimelineEntry(BaseModel):
    year: int
    publications: int
    cumulative: int
    phase: str
    velocity: float = 0.0
    acceleration: float = 0.0
    jerk: float = 0.0
    alert_level: str = "DARK"


class KeyEvent(BaseModel):
    year: int
    type: str
    label: str
    description: str


class Phase(BaseModel):
    id: str
    label: str
    years: List[int]
    color: str
    description: str


class SentinelReconstruction(BaseModel):
    narrative: str
    counterfactual: str
    key_insight: str


class BacktestResponse(BaseModel):
    compound: str
    compound_id: str
    cas_numbers: List[str]
    search_terms: str
    data_source: str
    retrieved_date: str
    total_publications: int
    first_publication_year: int
    first_detection_year: int
    first_lawsuit_year: int
    lead_time_years: int
    phases: List[Phase]
    timeline: List[TimelineEntry]
    key_events: List[KeyEvent]
    sentinel_reconstruction: SentinelReconstruction
    settlement_total_usd: int
    affected_population: int
    source_citations: List[str]


# ---------------------------------------------------------------------------
# SENTINEL signal computation
# ---------------------------------------------------------------------------

def _compute_sentinel_signals(timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute publication dynamics (velocity, acceleration, jerk, alert level)
    for each year in the timeline.

    Velocity: 3-year trailing average (papers/year)
    Acceleration: year-over-year change in velocity
    Jerk: year-over-year change in acceleration (inflection detection)
    Alert levels:
        DARK        - No publications ever recorded
        NOVEL       - First publications appear (velocity from zero)
        WATCH       - Sustained low-level publications
        ELEVATED    - Velocity accelerating or doubled
        HIGH        - Velocity > 10 papers/year
        CRITICAL    - Velocity > 20 papers/year or acceleration > 10 or jerk > 5
    """
    enriched = []
    prev_velocity = 0.0
    prev_acceleration = 0.0
    has_any_pubs = False

    for i, entry in enumerate(timeline):
        year = entry["year"]
        pubs = entry["publications"]
        cumulative = entry["cumulative"]
        phase = entry.get("phase", "")

        # 3-year trailing velocity
        window = [timeline[j]["publications"] for j in range(max(0, i - 2), i + 1)]
        velocity = round(sum(window) / len(window), 2)

        # Acceleration (change in velocity from prior year)
        acceleration = round(velocity - prev_velocity, 2) if i > 0 else 0.0

        # Jerk (change in acceleration - detects inflection points)
        jerk = round(acceleration - prev_acceleration, 2) if i > 1 else 0.0

        # Determine alert level
        if cumulative == 0:
            alert_level = "DARK"
        elif not has_any_pubs and pubs > 0:
            alert_level = "NOVEL"
        elif velocity > 20 or acceleration > 10 or jerk > 5:
            alert_level = "CRITICAL"
        elif velocity > 10:
            alert_level = "HIGH"
        elif acceleration > 2 or jerk > 2 or (prev_velocity > 0 and velocity > prev_velocity * 1.8):
            alert_level = "ELEVATED"
        elif cumulative > 0:
            alert_level = "WATCH"
        else:
            alert_level = "DARK"

        if pubs > 0:
            has_any_pubs = True

        enriched.append({
            **entry,
            "velocity": velocity,
            "acceleration": acceleration,
            "jerk": jerk,
            "alert_level": alert_level,
        })

        prev_velocity = velocity
        prev_acceleration = acceleration

    return enriched


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

_backtest_cache: Optional[Dict[str, Any]] = None


def _load_backtest() -> Dict[str, Any]:
    """Load and cache the GenX backtest data with computed signals."""
    global _backtest_cache
    if _backtest_cache is not None:
        return _backtest_cache

    if not GENX_BACKTEST_PATH.exists():
        logger.error(f"GenX backtest data not found: {GENX_BACKTEST_PATH}")
        return {}

    with open(GENX_BACKTEST_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Compute SENTINEL signals
    data["timeline"] = _compute_sentinel_signals(data["timeline"])

    _backtest_cache = data
    logger.info(f"Loaded GenX backtest: {len(data['timeline'])} years, "
                f"{len(data['key_events'])} events")
    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/backtest/genx", response_model=BacktestResponse)
async def get_genx_backtest() -> BacktestResponse:
    """
    Get the GenX (HFPO-DA) historical backtest.

    Returns the complete reconstruction of the GenX litigation timeline
    with publication dynamics, SENTINEL alert levels, key events, and
    the five-phase narrative from celebration to reckoning.

    Data source: PubMed (NCBI E-utilities), public court records, EPA filings.
    """
    data = _load_backtest()
    return BacktestResponse(**data)


@router.get("/backtest/genx/summary")
async def get_genx_summary() -> Dict[str, Any]:
    """Get a lightweight summary of the GenX backtest for cards/headers."""
    data = _load_backtest()
    return {
        "compound": data.get("compound", ""),
        "total_publications": data.get("total_publications", 0),
        "first_publication_year": data.get("first_publication_year", 0),
        "first_lawsuit_year": data.get("first_lawsuit_year", 0),
        "lead_time_years": data.get("lead_time_years", 0),
        "settlement_total_usd": data.get("settlement_total_usd", 0),
        "affected_population": data.get("affected_population", 0),
        "phase_count": len(data.get("phases", [])),
        "event_count": len(data.get("key_events", [])),
    }
