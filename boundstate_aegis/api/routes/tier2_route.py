#!/usr/bin/env python3
"""
Module: tier2_route
Purpose: Tier 2 substructure rules API endpoints for the AEGIS UI.
    Provides /api/v1/tier2/* endpoints exposing the Tier2Engine
    for pattern-based endpoint correlation, rule browsing,
    pattern definitions, and coverage reporting.

    Rev History:
        1.0.0 - Initial Tier 2 API routes

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-initialized engine singleton
_engine = None


def get_engine():
    """Get or initialize the Tier 2 engine (lazy singleton)."""
    global _engine
    if _engine is None:
        try:
            from boundstate_aegis.engines.tier2_substructure_engine import Tier2Engine
            from boundstate_aegis.api.routes.tier1_route import get_engine as get_tier1

            # Reuse the Tier 1 singleton to avoid duplicate EPA data in memory
            try:
                tier1 = get_tier1()
            except Exception:
                tier1 = None

            _engine = Tier2Engine(tier1_engine=tier1)
            logger.info(
                "Tier 2 engine initialized: %d rules mined",
                len(_engine.rules),
            )
        except Exception as e:
            logger.error("Failed to initialize Tier 2 engine: %s", e)
            raise HTTPException(
                status_code=503,
                detail=f"Tier 2 engine unavailable: {e}",
            )
    return _engine


# ---------------------------------------------------------------------------
# Request / Response models (API-layer wrappers)
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    """Request body for Tier 2 prediction."""
    smiles: str


class RulesPageResponse(BaseModel):
    """Paginated rules response."""
    rules: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/predict")
async def predict_endpoints(request: PredictRequest) -> Dict[str, Any]:
    """
    Given a SMILES string, return pattern-based endpoint correlations.

    Detects structural patterns (SMARTS + algorithmic), looks up
    mined rules from the literature corpus, and returns correlated
    endpoint buckets with Wilson score confidence intervals.

    This is NOT a prediction — it reports what the literature shows
    for compounds with similar substructures.
    """
    engine = get_engine()

    if not request.smiles or not request.smiles.strip():
        raise HTTPException(
            status_code=422,
            detail="SMILES string is required.",
        )

    result = engine.predict_endpoints(request.smiles.strip())
    return result.model_dump()


@router.get("/rules")
async def get_rules(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    pattern: Optional[str] = Query(
        None, description="Filter by pattern name"
    ),
    endpoint: Optional[str] = Query(
        None, description="Filter by endpoint bucket"
    ),
    min_confidence: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Minimum confidence threshold"
    ),
) -> RulesPageResponse:
    """
    Return all mined substructure rules, with optional filtering.

    Each rule maps a structural pattern to an endpoint bucket,
    with precursor counts and Wilson score confidence intervals.
    """
    engine = get_engine()
    all_rules = engine.rules

    # Apply filters
    filtered = all_rules
    if pattern:
        filtered = [r for r in filtered if r.pattern_name == pattern]
    if endpoint:
        filtered = [r for r in filtered if r.endpoint_bucket == endpoint]
    if min_confidence is not None:
        filtered = [r for r in filtered if r.confidence >= min_confidence]

    total = len(filtered)
    page = filtered[offset: offset + limit]

    return RulesPageResponse(
        rules=[r.model_dump() for r in page],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/patterns")
async def get_patterns() -> List[Dict[str, Any]]:
    """
    Return definitions of all patterns used in Tier 2 detection.

    Includes SMARTS patterns (functional groups), algorithmic
    features (chain length, F/C ratio), and compound classifications.
    """
    engine = get_engine()
    definitions = engine.get_patterns()
    return [d.model_dump() for d in definitions]


@router.get("/coverage")
async def get_coverage() -> Dict[str, Any]:
    """
    Return the Tier 2 preflight coverage report.

    Shows how many precursors were resolved to SMILES, which
    patterns have sufficient support, and lists unresolved
    precursor names. Use this to gauge how grounded the
    Tier 2 rules are.
    """
    engine = get_engine()
    coverage = engine.get_coverage()
    return coverage.model_dump()
