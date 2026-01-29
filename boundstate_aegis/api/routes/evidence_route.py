#!/usr/bin/env python3
"""
Module: evidence_route
Purpose: Evidence chain API endpoints for literature corpus access.
    Provides /api/v1/evidence/* endpoints for the EvidenceChain UI.
    Loads real evidence data from extracted literature corpus.

    Rev History:
        1.0.0 - Initial evidence chain routes

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

import yaml
from fastapi import APIRouter, Query
from pydantic import BaseModel

from boundstate_aegis.config import (
    PFAS_LIT_SUMMARY,
    ELLIS_EVIDENCE,
    MANUAL_EVIDENCE,
    LITERATURE_PAPER_COUNT,
    CONFIDENCE_MAPPING,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SourceStats(BaseModel):
    """Statistics about evidence sources."""
    total_papers: int
    extraction_method: str
    sources: List[Dict[str, Any]]
    coverage: Dict[str, int]


class EvidenceItem(BaseModel):
    """A single evidence citation."""
    source: str
    doi: Optional[str] = None
    year: Optional[int] = None
    confidence: float
    finding: str
    compound: str
    polymer: Optional[str] = None
    temperature_c: Optional[float] = None
    yield_pct: Optional[float] = None


class EvidenceChainResponse(BaseModel):
    """Evidence chain response."""
    material: str
    total_citations: int
    evidence_chain: List[EvidenceItem]
    confidence_score: float


# Global evidence cache
_evidence_cache: Optional[Dict[str, List[EvidenceItem]]] = None
_stats_cache: Optional[Dict[str, Any]] = None


def _normalize_confidence(conf_value: Any) -> float:
    """Convert confidence value to float."""
    if isinstance(conf_value, (int, float)):
        return float(conf_value)
    if isinstance(conf_value, str):
        return CONFIDENCE_MAPPING.get(conf_value.lower(), 0.5)
    return 0.5


def _extract_doi(references: List[str]) -> Optional[str]:
    """Extract DOI from reference list."""
    for ref in references:
        if ref.startswith("DOI:"):
            return ref[4:]
        if "10." in ref:
            return ref
    return None


def _load_pfas_lit_summary() -> List[Dict[str, Any]]:
    """Load literature summary JSON (supports both legacy array and new merged format)."""
    if not PFAS_LIT_SUMMARY.exists():
        logger.warning(f"Literature summary not found: {PFAS_LIT_SUMMARY}")
        return []

    try:
        with open(PFAS_LIT_SUMMARY, encoding="utf-8") as f:
            data = json.load(f)
        # Handle new merged format: {"metadata": ..., "evidence": [...]}
        if isinstance(data, dict) and "evidence" in data:
            evidence = data["evidence"]
            logger.info(f"Loaded {len(evidence)} evidence records from merged summary")
            return evidence
        logger.info(f"Loaded {len(data)} pathway records from literature summary")
        return data
    except Exception as e:
        logger.error(f"Failed to load literature summary: {e}")
        return []


def _load_ellis_evidence() -> List[Dict[str, Any]]:
    """Load Ellis thesis evidence JSON."""
    if not ELLIS_EVIDENCE.exists():
        logger.warning(f"Ellis evidence not found: {ELLIS_EVIDENCE}")
        return []

    try:
        with open(ELLIS_EVIDENCE, encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} evidence records from Ellis thesis")
        return data
    except Exception as e:
        logger.error(f"Failed to load Ellis evidence: {e}")
        return []


def _load_manual_evidence() -> List[Dict[str, Any]]:
    """Load manual evidence YAML."""
    if not MANUAL_EVIDENCE.exists():
        logger.warning(f"Manual evidence not found: {MANUAL_EVIDENCE}")
        return []

    try:
        with open(MANUAL_EVIDENCE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        evidence = data.get("evidence", []) if data else []
        logger.info(f"Loaded {len(evidence)} manual evidence records")
        return evidence
    except Exception as e:
        logger.error(f"Failed to load manual evidence: {e}")
        return []


def _build_evidence_database() -> Dict[str, List[EvidenceItem]]:
    """Build evidence database from all sources."""
    database: Dict[str, List[EvidenceItem]] = {}

    # Load from literature summary (low-medium confidence bulk data)
    for record in _load_pfas_lit_summary():
        polymer = record.get("polymer", "").upper()
        if not polymer:
            continue

        # Parse pathway to get product
        pathway = record.get("pathway", "")
        parts = pathway.split("→")
        product = parts[-1].strip() if parts else "unknown"

        item = EvidenceItem(
            source=record.get("references", ["literature"])[0] if record.get("references") else "literature",
            doi=_extract_doi(record.get("references", [])),
            confidence=_normalize_confidence(record.get("confidence", "low")),
            finding=record.get("snippet", "")[:300] if record.get("snippet") else pathway,
            compound=product,
            polymer=polymer,
        )

        if polymer not in database:
            database[polymer] = []
        database[polymer].append(item)

    # Load from Ellis evidence (high confidence curated data)
    for record in _load_ellis_evidence():
        polymer = record.get("polymer", "").upper()
        if not polymer:
            continue

        item = EvidenceItem(
            source=record.get("source_id", "Ellis2001"),
            doi="10.1038/35073634" if "Ellis" in record.get("source_id", "") else None,
            year=2001,
            confidence=_normalize_confidence(record.get("confidence", "high")),
            finding=record.get("text_fragment", record.get("mechanism", "")),
            compound=record.get("pfas_product", ""),
            polymer=polymer,
            temperature_c=record.get("temperature_c"),
            yield_pct=record.get("yield_pct"),
        )

        if polymer not in database:
            database[polymer] = []
        database[polymer].append(item)

    # Load from manual evidence (high confidence verified data)
    for record in _load_manual_evidence():
        polymer = record.get("polymer", "").upper()
        if not polymer:
            continue

        item = EvidenceItem(
            source=record.get("source_id", "manual"),
            doi="10.1038/35073634" if "THERMO_PTFE" in record.get("source_id", "") else None,
            year=2001 if "THERMO" in record.get("source_id", "") else 2003,
            confidence=_normalize_confidence(record.get("confidence", "high")),
            finding=record.get("text_fragment", ""),
            compound=record.get("pfas_product", ""),
            polymer=polymer,
            temperature_c=record.get("temperature_c"),
            yield_pct=record.get("yield_pct"),
        )

        if polymer not in database:
            database[polymer] = []
        database[polymer].append(item)

    # Sort each polymer's evidence by confidence (highest first)
    for polymer in database:
        database[polymer].sort(key=lambda x: x.confidence, reverse=True)

    return database


def _compute_stats(database: Dict[str, List[EvidenceItem]]) -> Dict[str, Any]:
    """Compute statistics from evidence database."""
    total_citations = sum(len(items) for items in database.values())

    # Count unique compounds
    compounds = set()
    for items in database.values():
        for item in items:
            if item.compound:
                compounds.add(item.compound.upper())

    # Count high-confidence items
    high_conf = sum(
        1 for items in database.values()
        for item in items
        if item.confidence >= 0.8
    )

    return {
        "total_papers": LITERATURE_PAPER_COUNT,
        "total_citations": total_citations,
        "polymers_covered": len(database),
        "compounds_identified": len(compounds),
        "high_confidence_citations": high_conf,
    }


def get_evidence_database() -> Dict[str, List[EvidenceItem]]:
    """Get or build evidence database (cached)."""
    global _evidence_cache
    if _evidence_cache is None:
        _evidence_cache = _build_evidence_database()
        logger.info(f"Built evidence database with {len(_evidence_cache)} polymers")
    return _evidence_cache


def get_stats() -> Dict[str, Any]:
    """Get or compute stats (cached)."""
    global _stats_cache
    if _stats_cache is None:
        _stats_cache = _compute_stats(get_evidence_database())
    return _stats_cache


@router.get("/sources", response_model=SourceStats)
async def get_evidence_sources() -> SourceStats:
    """Get statistics about the evidence database."""
    stats = get_stats()
    database = get_evidence_database()

    # Count evidence by source type
    peer_reviewed = 0
    regulatory = 0
    other = 0

    for items in database.values():
        for item in items:
            source = (item.source or "").lower()
            if "doi" in source or "et al" in source or any(x in source for x in ["ellis", "schlummer", "simon"]):
                peer_reviewed += 1
            elif any(x in source for x in ["epa", "oecd", "iarc", "eu"]):
                regulatory += 1
            else:
                other += 1

    return SourceStats(
        total_papers=stats["total_papers"],
        extraction_method="LLM-assisted literature extraction (Claude Haiku) + manual curation",
        sources=[
            {"type": "peer_reviewed", "count": peer_reviewed},
            {"type": "regulatory_documents", "count": regulatory},
            {"type": "curated_evidence", "count": other},
        ],
        coverage={
            "polymers": stats["polymers_covered"],
            "pfas_endpoints": stats["compounds_identified"],
            "total_pathway_citations": stats["total_citations"],
        },
    )


@router.get("/chain", response_model=EvidenceChainResponse)
async def get_evidence_chain(
    material: str = Query(..., description="Material to trace evidence for"),
    max_citations: int = Query(20, description="Maximum citations to return"),
) -> EvidenceChainResponse:
    """Get evidence chain for a material's PFAS pathways."""
    mat_upper = material.upper()
    database = get_evidence_database()

    # Try exact match first
    evidence = database.get(mat_upper, [])

    # Try partial match if no exact match
    if not evidence:
        for polymer, items in database.items():
            if mat_upper in polymer or polymer in mat_upper:
                evidence = items
                break

    # Limit to max_citations
    evidence = evidence[:max_citations]

    # Calculate overall confidence
    if evidence:
        confidence_score = sum(e.confidence for e in evidence) / len(evidence)
    else:
        confidence_score = 0.0

    return EvidenceChainResponse(
        material=mat_upper,
        total_citations=len(evidence),
        evidence_chain=evidence,
        confidence_score=round(confidence_score, 3),
    )
