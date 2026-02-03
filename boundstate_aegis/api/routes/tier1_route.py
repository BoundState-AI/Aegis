#!/usr/bin/env python3
"""
Module: tier1_route
Purpose: Tier 1 structural similarity API endpoints for the AEGIS UI.
    Provides /api/v1/tier1/* endpoints exposing the AEGISTier1Engine
    for structure-aware compound screening, neighborhood profiling,
    and evidence retrieval by structural similarity.

    Rev History:
        1.0.0 - Initial Tier 1 API routes

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
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Thread-safe lazy-initialized engine singleton
_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Get or initialize the Tier 1 engine (thread-safe lazy singleton)."""
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        # Double-check after acquiring lock
        if _engine is not None:
            return _engine
        try:
            from boundstate_aegis.engines.tier1_engine import AEGISTier1Engine
            _engine = AEGISTier1Engine()
            logger.info(
                "Tier 1 engine initialized: %d EPA compounds, %d pathways",
                len(_engine.epa_compounds),
                len(_engine.pathways),
            )
        except Exception as e:
            logger.error("Failed to initialize Tier 1 engine: %s", e)
            raise HTTPException(
                status_code=503,
                detail=f"Tier 1 engine unavailable: {e}",
            )
    return _engine


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request body for a full Tier 1 query."""
    smiles: Optional[str] = None
    compound_name: Optional[str] = None
    top_k: int = 10
    min_similarity: float = 0.4


class ResolveRequest(BaseModel):
    """Request body for SMILES resolution."""
    name: str


class EpaNeighbor(BaseModel):
    """A structurally similar compound from the EPA database."""
    name: str
    cas: Optional[str]
    similarity: float
    f_count: int
    c_count: int
    mw: float


class PathwayNeighbor(BaseModel):
    """A similar compound with known degradation pathways."""
    name: str
    similarity: float
    pathways_count: int
    endpoints: List[str]
    evidence_count: int


class EndpointEntry(BaseModel):
    """An endpoint in the neighborhood profile."""
    endpoint: str
    count: int
    fraction: float


class CitationEntry(BaseModel):
    """An evidence citation with DOI."""
    doi: str
    precursor: str
    product: str
    quote: str
    location: str


class Tier1QueryResponse(BaseModel):
    """Full response from a Tier 1 query."""
    query_name: str
    query_smiles: str
    risk_signal: str
    n_neighbors_with_pathways: int
    avg_similarity: float
    top_endpoints: List[EndpointEntry]
    mechanisms: Dict[str, int]
    similar_in_epa: List[EpaNeighbor]
    similar_with_pathways: List[PathwayNeighbor]
    evidence_citations: List[CitationEntry]
    disclaimer: str


class Tier1SummaryResponse(BaseModel):
    """Summary statistics for the engine."""
    epa_compounds: int
    fate_compounds: int
    pathways: int
    compounds_with_fingerprints: int


class ResolveResponse(BaseModel):
    """Response from SMILES resolution."""
    name: str
    smiles: Optional[str]
    resolved: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=Tier1SummaryResponse)
async def get_summary() -> Tier1SummaryResponse:
    """
    Get Tier 1 engine summary statistics.

    Returns counts of EPA compounds, fate compounds, pathways,
    and compounds with computed fingerprints.
    """
    engine = get_engine()

    fingerprinted = sum(
        1 for c in engine.compounds.values() if c.fingerprint is not None
    )

    return Tier1SummaryResponse(
        epa_compounds=len(engine.epa_compounds),
        fate_compounds=len(engine.compounds),
        pathways=len(engine.pathways),
        compounds_with_fingerprints=fingerprinted,
    )


@router.post("/query", response_model=Tier1QueryResponse)
async def query_compound(request: QueryRequest) -> Tier1QueryResponse:
    """
    Full Tier 1 structural similarity query.

    Provide either a SMILES string directly, or a compound name/CAS
    which will be resolved to SMILES first.

    Returns risk signal, structural neighbors, pathway endpoints,
    and evidence citations from the literature.
    """
    engine = get_engine()

    smiles = request.smiles
    name = request.compound_name or "Query"

    # If no SMILES provided, try to resolve from name
    if not smiles and request.compound_name:
        smiles = engine.resolve_smiles(request.compound_name)
        if not smiles:
            raise HTTPException(
                status_code=404,
                detail=f"Could not resolve SMILES for '{request.compound_name}'. "
                       f"Provide a SMILES string directly.",
            )

    if not smiles:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'smiles' or 'compound_name'.",
        )

    try:
        result = engine.query(smiles, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Tier1QueryResponse(
        query_name=result["query"]["name"],
        query_smiles=result["query"]["smiles"],
        risk_signal=result["risk_signal"],
        n_neighbors_with_pathways=result["n_neighbors_with_pathways"],
        avg_similarity=result["avg_similarity"],
        top_endpoints=[
            EndpointEntry(**ep) for ep in result["top_endpoints"]
        ],
        mechanisms=result["mechanisms"],
        similar_in_epa=[
            EpaNeighbor(**c) for c in result["similar_in_epa"]
        ],
        similar_with_pathways=[
            PathwayNeighbor(**p) for p in result["similar_with_pathways"]
        ],
        evidence_citations=[
            CitationEntry(**c) for c in result["evidence_citations"]
        ],
        disclaimer=result["disclaimer"],
    )


@router.get("/similar")
async def find_similar(
    smiles: str = Query(..., description="SMILES string to search"),
    top_k: int = Query(10, ge=1, le=50, description="Number of results"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Minimum Tanimoto similarity"),
) -> List[Dict[str, Any]]:
    """
    Find structurally similar compounds in the EPA PFAS database.

    Simple similarity search without pathway aggregation.
    """
    engine = get_engine()

    try:
        results = engine.find_similar_epa(smiles, top_k=top_k, min_similarity=min_similarity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [
        {
            "name": comp.name,
            "cas": comp.cas,
            "dtxsid": comp.dtxsid,
            "similarity": round(sim, 4),
            "f_count": comp.f_count,
            "c_count": comp.c_count,
            "mw": round(comp.mw, 1),
        }
        for comp, sim in results
    ]


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_smiles(request: ResolveRequest) -> ResolveResponse:
    """
    Resolve a compound name or CAS number to a SMILES string.

    Searches: manual SMILES → fate compounds → EPA database.
    """
    engine = get_engine()
    smiles = engine.resolve_smiles(request.name)

    return ResolveResponse(
        name=request.name,
        smiles=smiles,
        resolved=smiles is not None,
    )
