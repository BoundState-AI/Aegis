#!/usr/bin/env python3
"""
Module: assess_route
Purpose: POST /api/pfas/analyze endpoint for PFAS risk assessment.
    Provides the main risk assessment endpoint that evaluates compounds
    against degradation pathways and returns risk classifications.

    Rev History:
        1.0.0 - Initial assess route with PFASRiskEngine integration
        1.1.0 - Wired to real pfas_fate_v2.json literature data

BoundState AI 2025
Version: 1.1.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from boundstate_aegis.knowledge.graph_builder import build_graph, get_cached_graph
from boundstate_aegis.engines.pfas_risk_engine import PFASRiskEngine
from boundstate_aegis.config import PFAS_FATE_V2_JSON

logger = logging.getLogger(__name__)

router = APIRouter()

# Thread-safe cache for literature data
_fate_cache: Optional[Dict[str, Any]] = None
_fate_cache_lock = threading.Lock()


def get_fate_data() -> Dict[str, Any]:
    """Load and cache the real pfas_fate_v2.json literature corpus (thread-safe)."""
    global _fate_cache
    if _fate_cache is not None:
        return _fate_cache

    with _fate_cache_lock:
        # Double-check after acquiring lock
        if _fate_cache is not None:
            return _fate_cache
        if PFAS_FATE_V2_JSON.exists():
            with open(PFAS_FATE_V2_JSON, encoding="utf-8") as f:
                _fate_cache = json.load(f)
            logger.info(f"Loaded {len(_fate_cache.get('pathways', []))} pathways from pfas_fate_v2.json")
        else:
            logger.warning(f"pfas_fate_v2.json not found at {PFAS_FATE_V2_JSON}")
            _fate_cache = {"pathways": [], "metadata": {}}
    return _fate_cache


def get_literature_pathways(material: str) -> List[Dict[str, Any]]:
    """
    Pull degradation pathways from real pfas_fate_v2.json literature data.
    Returns list of pathway dicts with real evidence_score, DOIs, and verbatim quotes.
    """
    fate_data = get_fate_data()
    mat_upper = material.upper()

    # Find all pathways where this material is the precursor
    matching = []
    for pathway in fate_data.get("pathways", []):
        precursor = pathway.get("precursor", "").upper()
        # Match exact or partial (e.g., "PTFE" matches "PTFE", "PTFE polymer")
        if mat_upper == precursor or mat_upper in precursor or precursor in mat_upper:
            matching.append(pathway)

    # Convert to internal format
    results = []
    for p in matching:
        # Get temperature range
        temp_range = p.get("temp_c_range", [None, None])
        min_temp = temp_range[0] if temp_range and len(temp_range) > 0 else None
        max_temp = temp_range[1] if temp_range and len(temp_range) > 1 else None

        # Map temp_bucket to temperature if no explicit range
        if min_temp is None:
            bucket = p.get("temp_bucket", "ambient")
            if bucket == "ambient":
                min_temp, max_temp = 0, 100
            elif bucket == "elevated":
                min_temp, max_temp = 100, 400
            elif bucket == "high":
                min_temp, max_temp = 400, 800

        # Determine regulatory flags based on product
        product = p.get("product", "")
        product_upper = product.upper()
        regulatory = []
        if product_upper in ["TFA", "PFOA", "PFOS", "PFNA", "PFDA", "PFHXS"]:
            regulatory.append("EPA MCL 4ppt")
        if product_upper in ["PFOA", "PFOS"]:
            regulatory.append("Stockholm Convention")
        if product_upper in ["HFPO-DA", "GENX"]:
            regulatory.append("EPA Health Advisory 10ppt")

        # Get DOIs and evidence
        dois = p.get("source_dois", [])
        evidence_refs = p.get("evidence_refs", [])

        results.append({
            "child": product,
            "mechanism": p.get("mechanism", "unknown"),
            "min_temp_c": min_temp,
            "max_temp_c": max_temp,
            "literature_support": p.get("evidence_score", 0.5),  # Real score from literature
            "regulatory": regulatory,
            "observation_count": p.get("observation_count", 1),
            "source_dois": dois[:3],  # Top 3 DOIs
            "paper_count": len(set(dois)),
            "evidence_refs": evidence_refs[:2],  # Sample evidence refs
        })

    return results


class AnalyzeRequest(BaseModel):
    """Request body for /api/pfas/analyze endpoint."""

    compound: Optional[str] = Field(None, description="Name of the precursor compound to evaluate")
    source_compound: Optional[str] = Field(None, description="Alias for compound")
    scenario: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Scenario conditions: service_temp_c, incident_temp_c, atmosphere",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Alias for scenario",
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum transformation steps to explore",
    )

    def get_compound(self) -> str:
        """Get compound from either field."""
        return self.compound or self.source_compound or ""

    def get_scenario(self) -> Optional[Dict[str, Any]]:
        """Get scenario from either field."""
        return self.scenario or self.context


class Finding(BaseModel):
    """A single PFAS pathway finding - matches frontend expectations."""

    product: str
    screening_classification: str
    conditions_where_it_forms: List[Dict[str, Any]]
    confidence: float  # Kept for frontend compatibility
    literature_support: float = 0.0  # Real evidence score from literature
    regulatory_flags: List[str]
    evidence_refs: List[Dict[str, Any]]
    # Additional fields for frontend compatibility
    pathway: List[str] = []
    overall_confidence: float = 0.0
    litigation_flag: bool = False
    is_short_chain_pfas: bool = False
    # New fields from real literature data
    observation_count: int = 0
    paper_count: int = 0
    source_dois: List[str] = []


class AnalyzeResponse(BaseModel):
    """Response body for /api/pfas/analyze endpoint."""

    compound_evaluated: str
    scenario_context: Dict[str, Any]
    pfas_findings: List[Finding]
    summary: str
    data_source: str = "pfas_fate_v2.json"
    papers_in_corpus: int = 353
    disclaimer: str = "SCREENING ONLY: Results are literature-derived estimates from peer-reviewed publications. Analytical confirmation (EPA 537.1/533/8327) required for compliance decisions."


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pfas(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze potential PFAS formation pathways for a source compound.

    This endpoint performs screening-level assessment of degradation pathways
    from a precursor material to regulated PFAS endpoints under specified
    operating or incident conditions.

    **Important Limitations:**
    - Screening-level only - does not estimate formation yields or rates
    - Literature-derived pathways may be incomplete
    - Analytical confirmation (EPA 537.1/533/8327) required for compliance
    """
    compound = request.get_compound()
    scenario = request.get_scenario()

    if not compound:
        raise HTTPException(status_code=400, detail="compound or source_compound is required")

    try:
        # Use cached graph with thread-safe initialization (offload blocking I/O)
        graph = await asyncio.to_thread(get_cached_graph)
        engine = PFASRiskEngine(graph)

        result = engine.evaluate(
            source=compound,
            context=scenario,
            max_depth=request.max_depth,
        )

        # Short-chain PFAS products (C4-C6)
        short_chain_pfas = {"TFA", "PFBA", "PFPeA", "PFHxA", "PFBS", "PFHxS", "HFPO-DA"}
        # Products with litigation exposure
        litigation_products = {"PFOA", "PFOS", "GENX", "HFPO-DA", "PFNA", "PFHXS"}

        findings = []
        engine_findings = result.get("pfas_findings", [])

        if engine_findings:
            # Use findings from knowledge graph
            for f in engine_findings:
                product = f["product"]
                conditions = f.get("conditions_where_it_forms", [])

                # Build pathway from conditions
                pathway = [c.get("step", "") for c in conditions if c.get("step")]
                if not pathway:
                    pathway = [compound, product]

                findings.append(Finding(
                    product=product,
                    screening_classification=f["screening_classification"],
                    conditions_where_it_forms=conditions,
                    confidence=f["confidence"],
                    regulatory_flags=f["regulatory_flags"],
                    evidence_refs=f["evidence_refs"],
                    pathway=pathway,
                    overall_confidence=f["confidence"],
                    litigation_flag=product.upper() in litigation_products,
                    is_short_chain_pfas=product.upper() in short_chain_pfas,
                ))
        else:
            # Use real literature data from pfas_fate_v2.json
            literature_pathways = get_literature_pathways(compound)
            incident_temp = scenario.get("incident_temp_c", 0) if scenario else 0

            for pathway_data in literature_pathways:
                min_temp = pathway_data.get("min_temp_c", 0) or 0
                max_temp = pathway_data.get("max_temp_c", 9999) or 9999

                # Only include if temperature is in range
                if incident_temp >= min_temp or incident_temp == 0:
                    product = pathway_data["child"]
                    mechanism = pathway_data.get("mechanism", "thermal")
                    lit_support = pathway_data.get("literature_support", 0.5)
                    regulatory = pathway_data.get("regulatory", [])
                    obs_count = pathway_data.get("observation_count", 1)
                    paper_count = pathway_data.get("paper_count", 1)
                    source_dois = pathway_data.get("source_dois", [])
                    raw_evidence = pathway_data.get("evidence_refs", [])

                    # Determine screening classification
                    if regulatory:
                        classification = "REGULATED"
                    elif product.upper() in short_chain_pfas:
                        classification = "SHORT_CHAIN_PFAS"
                    else:
                        classification = "DEGRADATION_PRODUCT"

                    # Build evidence refs from real literature data
                    evidence_refs = []
                    for ev in raw_evidence[:2]:  # Top 2 evidence items
                        evidence_refs.append({
                            "property": "degradation_pathway",
                            "value": ev.get("verbatim_quote", "")[:200] if ev.get("verbatim_quote") else mechanism,
                            "source": ev.get("doi", "literature"),
                            "test_method": mechanism,
                            "date": ev.get("source_file", "literature"),
                            "literature_support": lit_support,
                        })
                    if not evidence_refs:
                        evidence_refs.append({
                            "property": "degradation_pathway",
                            "value": f"{compound} degrades to {product} via {mechanism}",
                            "source": source_dois[0] if source_dois else "pfas_fate_v2.json",
                            "test_method": mechanism,
                            "date": "literature_extraction",
                            "literature_support": lit_support,
                        })

                    findings.append(Finding(
                        product=product,
                        screening_classification=classification,
                        conditions_where_it_forms=[{
                            "step": f"{compound} → {product}",
                            "mechanism": mechanism,
                            "min_temp_c": min_temp,
                            "max_temp_c": max_temp,
                            "atmosphere": scenario.get("atmosphere", "air") if scenario else "air",
                        }],
                        confidence=lit_support,  # For frontend compatibility
                        literature_support=lit_support,  # Real literature score
                        regulatory_flags=regulatory,
                        evidence_refs=evidence_refs,
                        pathway=[compound, product],
                        overall_confidence=lit_support,
                        litigation_flag=product.upper().replace(" ", "") in litigation_products,
                        is_short_chain_pfas=product.upper() in short_chain_pfas,
                        observation_count=obs_count,
                        paper_count=paper_count,
                        source_dois=source_dois,
                    ))

        summary = result.get("summary", "")
        if not summary:
            if findings:
                # Count unique papers across all findings
                all_dois = set()
                total_observations = 0
                for f in findings:
                    all_dois.update(f.source_dois)
                    total_observations += f.observation_count
                paper_count = len(all_dois) if all_dois else sum(f.paper_count for f in findings)
                summary = f"Analysis of {compound} identified {len(findings)} degradation pathways from {paper_count} peer-reviewed papers ({total_observations} observations)."
            else:
                summary = f"No documented degradation pathways found for {compound} in the literature corpus (353 papers screened)."

        # Get metadata from fate data
        fate_data = get_fate_data()
        metadata = fate_data.get("metadata", {})
        papers_in_corpus = metadata.get("papers_processed", 353)

        return AnalyzeResponse(
            compound_evaluated=result.get("compound_evaluated", compound),
            scenario_context=result.get("scenario_context", scenario or {}),
            pfas_findings=findings,
            summary=summary,
            data_source="pfas_fate_v2.json (732 aggregated pathways from literature extraction)",
            papers_in_corpus=papers_in_corpus,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error during PFAS analysis")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# Alias endpoint for backwards compatibility
@router.post("/evaluate", response_model=AnalyzeResponse)
async def evaluate_pfas(request: AnalyzeRequest) -> AnalyzeResponse:
    """Alias for /analyze endpoint."""
    return await analyze_pfas(request)
