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
PFOA_BACKTEST_PATH = EVIDENCE_DIR / "pfoa_backtest.json"

# Available backtests for validation
AVAILABLE_BACKTESTS = {
    "genx": GENX_BACKTEST_PATH,
    "pfoa": PFOA_BACKTEST_PATH,
}

# Classified sentiment data (per-paper details for drill-down)
CLASSIFIED_PATHS = {
    "genx": EVIDENCE_DIR / "genx_sentiment_classified.json",
    "pfoa": EVIDENCE_DIR / "pfoa_sentiment_classified.json",
}

_classified_cache: Dict[str, List[Dict[str, Any]]] = {}


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
    sentiment: Optional[Dict[str, int]] = None
    cumulative_sentiment: Optional[float] = None
    normalized_sentiment: Optional[float] = None


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


class ValidationMetrics(BaseModel):
    """Metrics for validating SENTINEL signal timing."""
    first_elevated_to_settlement_years: Optional[int] = None
    first_critical_to_settlement_years: Optional[int] = None
    velocity_at_first_lawsuit: Optional[float] = None
    velocity_at_first_critical: Optional[float] = None
    acceleration_at_first_critical: Optional[float] = None


class LiabilityTier(BaseModel):
    """A single tier of liability exposure."""
    amount: int
    cases: List[str]
    note: str


class LiabilitySummary(BaseModel):
    """Three-tier liability structure for comparable risk assessment."""
    compound_specific: LiabilityTier
    associated_pfas_exposure: LiabilityTier
    total_pfas_landscape: LiabilityTier


class BacktestResponse(BaseModel):
    compound: str
    compound_id: str
    cas_numbers: List[str]
    search_terms: str
    data_source: str
    retrieved_date: str
    total_publications: int
    first_publication_year: int
    first_detection_year: Optional[int] = None  # GenX-specific
    first_elevated_year: Optional[int] = None   # PFOA-specific
    first_critical_year: Optional[int] = None   # PFOA-specific
    major_settlement_year: Optional[int] = None # PFOA-specific
    first_lawsuit_year: int
    lead_time_years: int
    phases: List[Phase]
    timeline: List[TimelineEntry]
    key_events: List[KeyEvent]
    sentinel_reconstruction: SentinelReconstruction
    settlement_total_usd: int
    liability_summary: Optional[LiabilitySummary] = None
    affected_population: int
    source_citations: List[str]
    validation_metrics: Optional[ValidationMetrics] = None


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

_backtest_cache: Dict[str, Dict[str, Any]] = {}


def _load_backtest(compound_id: str = "genx") -> Dict[str, Any]:
    """Load and cache backtest data with computed signals."""
    global _backtest_cache

    if compound_id in _backtest_cache:
        return _backtest_cache[compound_id]

    backtest_path = AVAILABLE_BACKTESTS.get(compound_id)
    if not backtest_path or not backtest_path.exists():
        logger.error(f"Backtest data not found for {compound_id}: {backtest_path}")
        return {}

    with open(backtest_path, encoding="utf-8") as f:
        data = json.load(f)

    # Compute SENTINEL signals
    data["timeline"] = _compute_sentinel_signals(data["timeline"])

    _backtest_cache[compound_id] = data
    logger.info(f"Loaded {compound_id} backtest: {len(data['timeline'])} years, "
                f"{len(data['key_events'])} events")
    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/backtests")
async def list_backtests() -> Dict[str, Any]:
    """List all available SENTINEL backtests for validation."""
    backtests = []
    for compound_id, path in AVAILABLE_BACKTESTS.items():
        if path.exists():
            data = _load_backtest(compound_id)
            backtests.append({
                "compound_id": compound_id,
                "compound": data.get("compound", ""),
                "total_publications": data.get("total_publications", 0),
                "first_lawsuit_year": data.get("first_lawsuit_year", 0),
                "lead_time_years": data.get("lead_time_years", 0),
                "settlement_total_usd": data.get("settlement_total_usd", 0),
                "liability_summary": data.get("liability_summary"),
            })
    return {
        "available_backtests": backtests,
        "methodology": "Publication dynamics (velocity, acceleration, jerk) as leading indicators of litigation exposure",
        "validated_prediction": "SENTINEL detects major settlement risk 10-15 years ahead, not first lawsuit timing",
    }


@router.get("/backtest/{compound_id}", response_model=BacktestResponse)
async def get_backtest(compound_id: str) -> BacktestResponse:
    """
    Get a historical backtest by compound ID.

    Available compounds: genx, pfoa

    Returns the complete reconstruction of the litigation timeline
    with publication dynamics, SENTINEL alert levels, and key events.
    """
    if compound_id not in AVAILABLE_BACKTESTS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Backtest not found for {compound_id}. Available: {list(AVAILABLE_BACKTESTS.keys())}"
        )
    data = _load_backtest(compound_id)
    return BacktestResponse(**data)


@router.get("/backtest/{compound_id}/summary")
async def get_backtest_summary(compound_id: str) -> Dict[str, Any]:
    """Get a lightweight summary of a backtest for cards/headers."""
    if compound_id not in AVAILABLE_BACKTESTS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Backtest not found for {compound_id}. Available: {list(AVAILABLE_BACKTESTS.keys())}"
        )
    data = _load_backtest(compound_id)
    return {
        "compound": data.get("compound", ""),
        "compound_id": compound_id,
        "total_publications": data.get("total_publications", 0),
        "first_publication_year": data.get("first_publication_year", 0),
        "first_lawsuit_year": data.get("first_lawsuit_year", 0),
        "first_elevated_year": data.get("first_elevated_year"),
        "first_critical_year": data.get("first_critical_year"),
        "lead_time_years": data.get("lead_time_years", 0),
        "settlement_total_usd": data.get("settlement_total_usd", 0),
        "liability_summary": data.get("liability_summary"),
        "affected_population": data.get("affected_population", 0),
        "phase_count": len(data.get("phases", [])),
        "event_count": len(data.get("key_events", [])),
        "validation_metrics": data.get("validation_metrics"),
    }


# ---------------------------------------------------------------------------
# Paper drill-down endpoint
# ---------------------------------------------------------------------------

def _load_classified(compound_id: str) -> List[Dict[str, Any]]:
    """Load and cache classified paper data for drill-down."""
    global _classified_cache

    if compound_id in _classified_cache:
        return _classified_cache[compound_id]

    path = CLASSIFIED_PATHS.get(compound_id)
    if not path or not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    _classified_cache[compound_id] = data
    logger.info(f"Loaded {compound_id} classified papers: {len(data)} papers")
    return data


@router.get("/backtest/{compound_id}/papers/{year}")
async def get_papers_by_year(compound_id: str, year: int) -> Dict[str, Any]:
    """
    Get individual classified papers for a compound in a given year.

    Returns paper details including title, journal, PMID, sentiment
    category, confidence, and classification reasoning. Used for
    drill-down from the sentiment chart tooltip.
    """
    if compound_id not in CLASSIFIED_PATHS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Classified data not found for {compound_id}. Available: {list(CLASSIFIED_PATHS.keys())}"
        )

    classified = _load_classified(compound_id)
    papers = [p for p in classified if p.get("year") == year]

    # Sort: alarm/reckoning first, then by confidence descending
    category_order = {"RECKONING": 0, "ALARM": 1, "QUESTIONING": 2, "DETECTION": 3, "UTILITY": 4, "CELEBRATION": 5}
    papers.sort(key=lambda p: (category_order.get(p.get("category", "").upper(), 9), -p.get("confidence", 0)))

    return {
        "compound_id": compound_id,
        "year": year,
        "total": len(papers),
        "papers": [
            {
                "pmid": p.get("pmid", ""),
                "title": p.get("title", ""),
                "journal": p.get("journal", ""),
                "category": p.get("category", ""),
                "confidence": p.get("confidence", 0),
                "reasoning": p.get("reasoning", ""),
            }
            for p in papers
        ],
    }


# Legacy endpoints for backwards compatibility
@router.get("/backtest/genx", response_model=BacktestResponse, include_in_schema=False)
async def get_genx_backtest_legacy() -> BacktestResponse:
    """Legacy endpoint - redirects to /backtest/genx."""
    return await get_backtest("genx")


@router.get("/backtest/genx/summary", include_in_schema=False)
async def get_genx_summary_legacy() -> Dict[str, Any]:
    """Legacy endpoint - redirects to /backtest/genx/summary."""
    return await get_backtest_summary("genx")
