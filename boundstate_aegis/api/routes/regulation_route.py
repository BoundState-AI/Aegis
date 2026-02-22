#!/usr/bin/env python3
"""
Module: regulation_route
Purpose: Regulatory status query endpoints for compound compliance checking.
    Provides endpoints for querying compound regulation across jurisdictions.

    Rev History:
        1.0.0 - Initial regulation routes

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
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from boundstate_aegis.knowledge.graph_builder import build_graph
from boundstate_aegis.engines.regulation_checker import (
    check_regulatory_status,
    get_regulatory_summary,
)
from boundstate_aegis.engines.pfas_risk_engine import PFASRiskEngine

logger = logging.getLogger(__name__)

router = APIRouter()


class RegulatoryStatusResponse(BaseModel):
    """Regulatory status for a compound."""

    compound_name: str
    is_pfas: bool
    is_short_chain_pfas: bool
    regulated_in: List[str]
    jurisdictions: List[str]
    litigation_status: str
    summary: str


@router.get("/status/{compound}")
async def get_compound_regulatory_status(compound: str) -> RegulatoryStatusResponse:
    """Get regulatory status for a specific compound."""
    try:
        graph = build_graph()
        status = check_regulatory_status(compound, graph)

        return RegulatoryStatusResponse(
            compound_name=status.compound_name,
            is_pfas=status.is_pfas,
            is_short_chain_pfas=status.is_short_chain_pfas,
            regulated_in=status.regulated_in,
            jurisdictions=[j.value for j in status.jurisdictions],
            litigation_status=status.litigation_status.value,
            summary=get_regulatory_summary(status),
        )

    except Exception:
        logger.exception("Error checking regulatory status")
        raise HTTPException(status_code=500, detail="Regulatory status check failed")


class DisclaimerResponse(BaseModel):
    """Regulatory disclaimer text."""

    disclaimer: str


@router.get("/disclaimer")
async def get_disclaimer() -> DisclaimerResponse:
    """Get the full regulatory disclaimer text."""
    return DisclaimerResponse(
        disclaimer=PFASRiskEngine.get_regulatory_disclaimer()
    )
