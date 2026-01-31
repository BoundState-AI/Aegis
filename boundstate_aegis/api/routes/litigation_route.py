#!/usr/bin/env python3
"""
Module: litigation_route
Purpose: Litigation risk forecasting API endpoints using publication dynamics.
    Provides /api/v1/litigation/* endpoints for the LitigationRisk UI.

    Risk model based on publication dynamics (physics-inspired metrics):
    - Position: Total papers (accumulated research attention)
    - Velocity: Papers per year (current activity)
    - Acceleration: Change in velocity (momentum)
    - Jerk: Change in acceleration (inflection detection)

    Rev History:
        1.0.0 - Initial litigation risk routes with publication dynamics
        1.0.1 - Terminology cleanup

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

from boundstate_aegis.config import PFAS_LIT_SUMMARY, EVIDENCE_DIR
from boundstate_aegis.analytics.publication_dynamics import PublicationDynamics

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize publication dynamics analyzer
_dynamics: Optional[PublicationDynamics] = None


def get_dynamics() -> PublicationDynamics:
    """Get or initialize publication dynamics analyzer."""
    global _dynamics
    if _dynamics is None:
        pdf_dir = Path("D:/chemours_PFAS/pfas lit")
        _dynamics = PublicationDynamics(PFAS_LIT_SUMMARY, pdf_dir if pdf_dir.exists() else None)
        logger.info(f"Initialized publication dynamics with {len(_dynamics.entries)} entries")
    return _dynamics


class SimilarCase(BaseModel):
    """A similar litigation case."""
    case: str
    settlement: int
    year: int
    relevance: float


class PublicationMetrics(BaseModel):
    """Publication dynamics metrics."""
    position: int
    velocity: float
    acceleration: float
    jerk: float
    content_health: int
    content_contamination: int
    content_regulatory: int


class LitigationForecast(BaseModel):
    """Litigation risk forecast response."""
    compound: str
    probability_12_months: float
    probability_24_months: float
    probability_36_months: float
    risk_level: str
    confidence_low: float
    confidence_high: float
    key_drivers: List[str]
    estimated_exposure_usd: int
    similar_cases: List[SimilarCase]
    publication_metrics: PublicationMetrics
    methodology: str = (
        "Risk calculated using publication dynamics from PubMed data: "
        "position (total papers), velocity (papers/year), acceleration "
        "(momentum), jerk (inflection), and content signals. Preview model."
    )
    is_preview: bool = True


class ForecastRequest(BaseModel):
    """Request body for litigation forecast."""
    compound: str
    production_volume_lbs: int = 100000
    exposure_pathways: List[str] = ["water"]


# Known litigation settlements (real data)
SIMILAR_CASES = [
    SimilarCase(case="State of Ohio v. DuPont", settlement=670_000_000, year=2017, relevance=0.92),
    SimilarCase(case="3M PFAS Settlement (Public Water)", settlement=10_300_000_000, year=2023, relevance=0.88),
    SimilarCase(case="Chemours Environmental Remediation", settlement=2_200_000_000, year=2022, relevance=0.85),
    SimilarCase(case="AFFF Firefighting Foam MDL", settlement=1_185_000_000, year=2023, relevance=0.78),
    SimilarCase(case="Wolverine World Wide Contamination", settlement=165_000_000, year=2020, relevance=0.72),
]

# Base exposure estimates (from settlement data patterns)
BASE_EXPOSURE = {
    "PFOA": 500_000_000,
    "PFOS": 450_000_000,
    "GENX": 200_000_000,
    "PFA": 300_000_000,
    "PTFE": 150_000_000,
    "PVDF": 100_000_000,
    "FEP": 80_000_000,
    "TFA": 50_000_000,
    "HF": 40_000_000,
}


def calculate_dynamics_risk(metrics: Dict[str, Any]) -> float:
    """
    Calculate risk score from publication dynamics.

    Weighted combination of normalized metrics.
    """
    # Normalize each metric to 0-1 scale
    pos_norm = min(metrics["position"] / 100, 1.0)
    vel_norm = min(metrics["velocity"] / 20, 1.0)
    acc_norm = min(max(metrics["acceleration"] + 10, 0) / 40, 1.0)
    jerk_norm = min(max(metrics["jerk"] + 10, 0) / 40, 1.0)

    content = metrics.get("content_signals", {})
    content_score = (
        content.get("health", 0) * 0.4 +
        content.get("contamination", 0) * 0.3 +
        content.get("regulatory", 0) * 0.3
    )
    content_norm = min(content_score / 50, 1.0)

    # Weighted combination
    risk = (
        0.15 * pos_norm +       # Position: established compounds
        0.30 * vel_norm +       # Velocity: active research (most important)
        0.25 * acc_norm +       # Acceleration: momentum
        0.15 * jerk_norm +      # Jerk: inflection points
        0.15 * content_norm     # Content signals
    )

    return min(risk, 0.95)


def generate_key_drivers(
    compound: str,
    metrics: Dict[str, Any],
    exposure_pathways: List[str]
) -> List[str]:
    """Generate key drivers based on publication dynamics and pathways."""
    drivers = []

    # Add dynamics-based drivers
    if metrics["velocity"] > 10:
        drivers.append(f"High research velocity: {metrics['velocity']:.1f} papers/year on {compound}")

    if metrics["acceleration"] > 5:
        drivers.append(f"Accelerating research attention: +{metrics['acceleration']:.1f} papers/year growth")

    if metrics["jerk"] > 5:
        drivers.append(f"Emerging inflection point: research momentum increasing rapidly")

    content = metrics.get("content_signals", {})
    if content.get("health", 0) > 5:
        drivers.append(f"Health effects documented in {content['health']} studies")

    if content.get("regulatory", 0) > 10:
        drivers.append(f"Regulatory attention: {content['regulatory']} papers discuss regulations")

    if content.get("contamination", 0) > 5:
        drivers.append(f"Contamination studies: {content['contamination']} papers on environmental presence")

    # Add pathway-based drivers
    if "water" in exposure_pathways:
        drivers.append("EPA drinking water MCL enforcement (4 ppt PFOA/PFOS)")
        drivers.append("Public water utility class actions expanding")

    if "air" in exposure_pathways:
        drivers.append("Stack emission monitoring requirements expanding")

    if "soil" in exposure_pathways:
        drivers.append("CERCLA hazardous substance designation pending")

    if "consumer_products" in exposure_pathways:
        drivers.append("Consumer product liability exposure increasing")

    # Limit to top 5
    return drivers[:5]


@router.post("/forecast", response_model=LitigationForecast)
async def forecast_litigation(request: ForecastRequest) -> LitigationForecast:
    """
    Generate litigation risk forecast for a compound.

    Uses publication dynamics (position, velocity, acceleration, jerk)
    from literature analysis to estimate litigation probability.
    """
    compound = request.compound.upper()
    dynamics = get_dynamics()

    # Get publication metrics
    metrics = dynamics.get_all_metrics(compound)

    # Calculate base risk from publication dynamics
    base_risk = calculate_dynamics_risk(metrics)

    # Adjust risk based on production volume
    volume_factor = min(request.production_volume_lbs / 100000, 2.0)

    # Adjust risk based on exposure pathways
    pathway_multiplier = 1.0
    if "water" in request.exposure_pathways:
        pathway_multiplier *= 1.3
    if "air" in request.exposure_pathways:
        pathway_multiplier *= 1.1
    if "soil" in request.exposure_pathways:
        pathway_multiplier *= 1.15
    if "consumer_products" in request.exposure_pathways:
        pathway_multiplier *= 1.2

    # Calculate probabilities over time
    adjusted_risk = min(base_risk * volume_factor * pathway_multiplier, 0.95)
    prob_12 = adjusted_risk * 0.4
    prob_24 = adjusted_risk * 0.7
    prob_36 = adjusted_risk * 0.9

    # Determine risk level
    if prob_24 >= 0.7:
        risk_level = "CRITICAL"
    elif prob_24 >= 0.5:
        risk_level = "HIGH"
    elif prob_24 >= 0.3:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Calculate exposure estimate
    base_exposure = BASE_EXPOSURE.get(compound, 50_000_000)
    exposure = int(base_exposure * volume_factor * pathway_multiplier)

    # Generate key drivers
    key_drivers = generate_key_drivers(compound, metrics, request.exposure_pathways)

    # Select relevant similar cases
    cases = [c for c in SIMILAR_CASES if c.relevance > 0.7][:4]

    # Build publication metrics for response
    content = metrics.get("content_signals", {})
    pub_metrics = PublicationMetrics(
        position=metrics["position"],
        velocity=round(metrics["velocity"], 2),
        acceleration=round(metrics["acceleration"], 2),
        jerk=round(metrics["jerk"], 2),
        content_health=content.get("health", 0),
        content_contamination=content.get("contamination", 0),
        content_regulatory=content.get("regulatory", 0),
    )

    return LitigationForecast(
        compound=compound,
        probability_12_months=round(prob_12, 3),
        probability_24_months=round(prob_24, 3),
        probability_36_months=round(prob_36, 3),
        risk_level=risk_level,
        confidence_low=round(prob_24 * 0.8, 3),
        confidence_high=round(min(prob_24 * 1.2, 0.99), 3),
        key_drivers=key_drivers,
        estimated_exposure_usd=exposure,
        similar_cases=cases,
        publication_metrics=pub_metrics,
    )


@router.get("/dynamics/{compound}")
async def get_compound_dynamics(compound: str) -> Dict[str, Any]:
    """Get raw publication dynamics for a compound."""
    dynamics = get_dynamics()
    return dynamics.get_all_metrics(compound)


@router.get("/ranking")
async def get_compound_ranking() -> List[Dict[str, Any]]:
    """Get all compounds ranked by publication dynamics risk signal."""
    dynamics = get_dynamics()
    return dynamics.get_compound_ranking()


# ---------------------------------------------------------------------------
# SENTINEL: GenX Historical Backtest
# ---------------------------------------------------------------------------

GENX_BACKTEST_PATH = EVIDENCE_DIR / "genx_backtest.json"

_backtest_cache: Optional[Dict[str, Any]] = None


def _compute_sentinel_signals(
    timeline: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compute publication velocity, acceleration, and alert level per year."""
    enriched = []
    prev_velocity = 0.0
    has_any_pubs = False

    for i, entry in enumerate(timeline):
        pubs = entry["publications"]
        cumulative = entry["cumulative"]

        # 3-year trailing velocity
        window = [timeline[j]["publications"] for j in range(max(0, i - 2), i + 1)]
        velocity = round(sum(window) / len(window), 2)

        # Acceleration
        acceleration = round(velocity - prev_velocity, 2) if i > 0 else 0.0

        # Alert level
        if cumulative == 0:
            alert_level = "DARK"
        elif not has_any_pubs and pubs > 0:
            alert_level = "NOVEL"
        elif velocity > 20 or acceleration > 10:
            alert_level = "CRITICAL"
        elif velocity > 10:
            alert_level = "HIGH"
        elif acceleration > 2 or (prev_velocity > 0 and velocity > prev_velocity * 1.8):
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
            "alert_level": alert_level,
        })
        prev_velocity = velocity

    return enriched


def _load_backtest() -> Dict[str, Any]:
    """Load and cache GenX backtest data with computed SENTINEL signals."""
    global _backtest_cache
    if _backtest_cache is not None:
        return _backtest_cache

    if not GENX_BACKTEST_PATH.exists():
        logger.error(f"GenX backtest data not found: {GENX_BACKTEST_PATH}")
        return {}

    with open(GENX_BACKTEST_PATH, encoding="utf-8") as f:
        data = json.load(f)

    data["timeline"] = _compute_sentinel_signals(data["timeline"])
    _backtest_cache = data
    logger.info(
        f"Loaded GenX backtest: {len(data['timeline'])} years, "
        f"{len(data['key_events'])} events"
    )
    return data


@router.get("/backtest/genx")
async def get_genx_backtest() -> Dict[str, Any]:
    """
    GenX (HFPO-DA) historical backtest.

    Reconstructs what SENTINEL would have shown during the GenX
    contamination timeline (2006-2025). Publication data from PubMed;
    events from public court records, EPA filings, and news sources.
    """
    return _load_backtest()
