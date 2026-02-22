#!/usr/bin/env python3
"""
Module: pathway_route
Purpose: Pathway query endpoints for knowledge graph exploration.
    Provides endpoints for tracing degradation pathways, querying
    downstream products, and exploring compound relationships.

    Rev History:
        1.0.0 - Initial pathway routes with trace_pathways endpoint

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from boundstate_aegis.knowledge.graph_builder import get_cached_graph
from boundstate_aegis.knowledge.graph_queries import (
    trace_pathways,
    get_downstream_products,
    get_upstream_sources,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class PathwayResult(BaseModel):
    """A single pathway from source to target."""

    path: List[str]
    confidence: float
    conditions: List[Dict[str, Any]]
    evidence_refs: List[Dict[str, Any]]


class TraceResponse(BaseModel):
    """Response for pathway tracing."""

    source: str
    pathways: List[PathwayResult]
    total_found: int


@router.get("/trace/{compound}")
async def trace_compound_pathways(
    compound: str,
    max_depth: int = Query(default=3, ge=1, le=10),
    max_results: int = Query(default=100, ge=1, le=1000),
) -> TraceResponse:
    """
    Trace potential degradation pathways from a source compound to PFAS endpoints.
    """
    try:
        # Offload blocking graph operations to thread pool
        graph = await asyncio.to_thread(get_cached_graph)
        pathways = await asyncio.to_thread(
            trace_pathways,
            graph=graph,
            start_compound=compound,
            max_depth=max_depth,
            max_results=max_results,
        )

        return TraceResponse(
            source=compound,
            pathways=[
                PathwayResult(
                    path=p["path"],
                    confidence=p["confidence"],
                    conditions=p["conditions"],
                    evidence_refs=p["evidence_refs"],
                )
                for p in pathways
            ],
            total_found=len(pathways),
        )

    except Exception:
        logger.exception("Error tracing pathways")
        raise HTTPException(status_code=500, detail="Pathway tracing failed")


class CompoundListResponse(BaseModel):
    """Response for compound list queries."""

    source: str
    compounds: List[str]
    count: int


@router.get("/downstream/{compound}")
async def get_downstream(
    compound: str,
    max_depth: int = Query(default=3, ge=1, le=10),
) -> CompoundListResponse:
    """Get all compounds reachable from a source compound."""
    try:
        # Offload blocking graph operations to thread pool
        graph = await asyncio.to_thread(get_cached_graph)
        products = await asyncio.to_thread(get_downstream_products, graph, compound, max_depth)

        return CompoundListResponse(
            source=compound,
            compounds=products,
            count=len(products),
        )

    except Exception:
        logger.exception("Error getting downstream products")
        raise HTTPException(status_code=500, detail="Downstream query failed")


@router.get("/upstream/{compound}")
async def get_upstream(
    compound: str,
    max_depth: int = Query(default=3, ge=1, le=10),
) -> CompoundListResponse:
    """Get all compounds that can degrade to a target compound."""
    try:
        # Offload blocking graph operations to thread pool
        graph = await asyncio.to_thread(get_cached_graph)
        sources = await asyncio.to_thread(get_upstream_sources, graph, compound, max_depth)

        return CompoundListResponse(
            source=compound,
            compounds=sources,
            count=len(sources),
        )

    except Exception:
        logger.exception("Error getting upstream sources")
        raise HTTPException(status_code=500, detail="Upstream query failed")
