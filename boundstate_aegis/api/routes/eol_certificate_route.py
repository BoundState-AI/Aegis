#!/usr/bin/env python3
"""
Module: eol_certificate_route
Purpose: EOL Proof Certificate API endpoints for PFAS destruction proof.
    Provides /api/v1/eol/* endpoints for generating End-of-Life certificates
    that prove precursor → terminal product → destruction viability → IP exposure.

    Rev History:
        1.0.0 - Initial EOL certificate routes

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: Claude Opus 4.6 <noreply@anthropic.com>

"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from boundstate_aegis.engines.eol_certificate_generator import (
    EOLCertificateGenerator,
    EOLProofCertificate,
)
from boundstate_aegis.knowledge.destruction_queries import (
    get_all_technologies,
    get_technology,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Thread-safe lazy singleton for generator
_generator: Optional[EOLCertificateGenerator] = None
_generator_lock = threading.Lock()


def _get_generator() -> EOLCertificateGenerator:
    """Get or create the EOL certificate generator (thread-safe)."""
    global _generator
    if _generator is not None:
        return _generator
    with _generator_lock:
        if _generator is not None:
            return _generator
        _generator = EOLCertificateGenerator()
        logger.info("EOL certificate generator initialized")
    return _generator


# ─── Request / Response Models ────────────────────────────────────────────────

class GenerateCertificateRequest(BaseModel):
    """Request body for certificate generation."""
    precursor: str = Field(..., description="Source compound (e.g., 'HFO-1234yf')")
    precursor_type: str = Field(
        default="fluorochemical",
        description="Type description (e.g., 'HFO refrigerant')",
    )
    target_product: str = Field(
        default="TFA",
        description="Terminal PFAS product to trace to",
    )


class TechnologySummary(BaseModel):
    """Brief technology listing."""
    id: str
    name: str
    acronym: Optional[str] = None
    trl: int
    mechanism: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=EOLProofCertificate)
async def generate_certificate(request: GenerateCertificateRequest):
    """
    Generate an EOL Proof Certificate for a precursor compound.

    Traces degradation pathway, proves destruction viability,
    and analyzes Chemours IP exposure.
    """
    try:
        generator = _get_generator()
        cert = generator.generate(
            precursor=request.precursor,
            precursor_type=request.precursor_type,
            target_product=request.target_product,
        )
        return cert
    except Exception as e:
        logger.exception("Failed to generate EOL certificate for %s", request.precursor)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technologies", response_model=List[TechnologySummary])
async def list_technologies():
    """List all available destruction technologies."""
    techs = get_all_technologies()
    return [
        TechnologySummary(
            id=t.id,
            name=t.name,
            acronym=t.acronym,
            trl=t.trl,
            mechanism=t.mechanism,
        )
        for t in techs
    ]


@router.get("/technologies/{tech_id}")
async def get_technology_detail(tech_id: str):
    """Get detailed information about a specific destruction technology."""
    tech = get_technology(tech_id)
    if tech is None:
        raise HTTPException(status_code=404, detail=f"Technology '{tech_id}' not found")
    return tech.to_summary()
