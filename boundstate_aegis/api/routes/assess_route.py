#!/usr/bin/env python3
"""
Module: assess_route
Purpose: POST /api/pfas/analyze endpoint for PFAS risk assessment.
    Provides the main risk assessment endpoint that evaluates compounds
    against degradation pathways and returns risk classifications.

    Rev History:
        1.0.0 - Initial assess route with PFASRiskEngine integration

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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from boundstate_aegis.knowledge.graph_builder import build_graph
from boundstate_aegis.engines.pfas_risk_engine import PFASRiskEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Fallback degradation pathway data when knowledge graph is sparse
FALLBACK_PATHWAYS: Dict[str, List[Dict[str, Any]]] = {
    "PTFE": [
        {"child": "TFA", "mechanism": "thermal_oxidation", "min_temp_c": 400, "max_temp_c": 600, "confidence": 0.92, "regulatory": ["EPA MCL 4ppt"]},
        {"child": "HF", "mechanism": "thermal_decomposition", "min_temp_c": 400, "max_temp_c": 800, "confidence": 0.95, "regulatory": []},
        {"child": "CF4", "mechanism": "thermal_decomposition", "min_temp_c": 600, "max_temp_c": 800, "confidence": 0.85, "regulatory": []},
        {"child": "COF2", "mechanism": "thermal_oxidation", "min_temp_c": 500, "max_temp_c": 700, "confidence": 0.78, "regulatory": []},
    ],
    "PVDF": [
        {"child": "HF", "mechanism": "thermal_decomposition", "min_temp_c": 350, "max_temp_c": 500, "confidence": 0.90, "regulatory": []},
        {"child": "VDF monomer", "mechanism": "depolymerization", "min_temp_c": 400, "max_temp_c": 600, "confidence": 0.75, "regulatory": []},
    ],
    "FEP": [
        {"child": "TFA", "mechanism": "thermal_oxidation", "min_temp_c": 400, "max_temp_c": 600, "confidence": 0.88, "regulatory": ["EPA MCL 4ppt"]},
        {"child": "HF", "mechanism": "thermal_decomposition", "min_temp_c": 400, "max_temp_c": 800, "confidence": 0.92, "regulatory": []},
        {"child": "CF4", "mechanism": "thermal_decomposition", "min_temp_c": 600, "max_temp_c": 800, "confidence": 0.80, "regulatory": []},
        {"child": "PFOA traces", "mechanism": "processing_residual", "min_temp_c": 0, "max_temp_c": 100, "confidence": 0.45, "regulatory": ["Stockholm Convention", "EPA MCL 4ppt"]},
    ],
    "PFA": [
        {"child": "TFA", "mechanism": "thermal_oxidation", "min_temp_c": 400, "max_temp_c": 600, "confidence": 0.90, "regulatory": ["EPA MCL 4ppt"]},
        {"child": "HF", "mechanism": "thermal_decomposition", "min_temp_c": 400, "max_temp_c": 800, "confidence": 0.93, "regulatory": []},
        {"child": "HFPO-DA", "mechanism": "thermal_degradation", "min_temp_c": 300, "max_temp_c": 500, "confidence": 0.65, "regulatory": ["EPA Health Advisory 10ppt"]},
        {"child": "PFOA traces", "mechanism": "processing_residual", "min_temp_c": 0, "max_temp_c": 100, "confidence": 0.50, "regulatory": ["Stockholm Convention", "EPA MCL 4ppt"]},
    ],
    "ETFE": [
        {"child": "HF", "mechanism": "thermal_decomposition", "min_temp_c": 400, "max_temp_c": 600, "confidence": 0.85, "regulatory": []},
        {"child": "TFA", "mechanism": "thermal_oxidation", "min_temp_c": 450, "max_temp_c": 650, "confidence": 0.70, "regulatory": ["EPA MCL 4ppt"]},
    ],
    "R-134A": [
        {"child": "TFA", "mechanism": "atmospheric_oxidation", "min_temp_c": 0, "max_temp_c": 100, "confidence": 0.85, "regulatory": ["EPA MCL 4ppt"]},
        {"child": "HF", "mechanism": "combustion", "min_temp_c": 600, "max_temp_c": 1000, "confidence": 0.90, "regulatory": []},
    ],
    "OPTEON YF": [
        {"child": "TFA", "mechanism": "atmospheric_oxidation", "min_temp_c": 0, "max_temp_c": 100, "confidence": 0.92, "regulatory": ["EPA MCL 4ppt"]},
        {"child": "HF", "mechanism": "thermal_decomposition", "min_temp_c": 400, "max_temp_c": 800, "confidence": 0.88, "regulatory": []},
    ],
}


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
    confidence: float
    regulatory_flags: List[str]
    evidence_refs: List[Dict[str, Any]]
    # Additional fields for frontend compatibility
    pathway: List[str] = []
    overall_confidence: float = 0.0
    litigation_flag: bool = False
    is_short_chain_pfas: bool = False


class AnalyzeResponse(BaseModel):
    """Response body for /api/pfas/analyze endpoint."""

    compound_evaluated: str
    scenario_context: Dict[str, Any]
    pfas_findings: List[Finding]
    summary: str
    disclaimer: str = "SCREENING ONLY: Results are literature-derived estimates. Analytical confirmation (EPA 537.1/533/8327) required for compliance decisions."


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
        graph = build_graph()
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
            # Use fallback pathway data
            fallback = FALLBACK_PATHWAYS.get(compound.upper(), [])
            incident_temp = scenario.get("incident_temp_c", 0) if scenario else 0

            for pathway_data in fallback:
                min_temp = pathway_data.get("min_temp_c", 0)
                max_temp = pathway_data.get("max_temp_c", 9999)

                # Only include if temperature is in range
                if incident_temp >= min_temp or incident_temp == 0:
                    product = pathway_data["child"]
                    mechanism = pathway_data.get("mechanism", "thermal")
                    confidence = pathway_data.get("confidence", 0.5)
                    regulatory = pathway_data.get("regulatory", [])

                    # Determine screening classification
                    if regulatory:
                        classification = "REGULATED"
                    elif product.upper() in short_chain_pfas:
                        classification = "SHORT_CHAIN_PFAS"
                    else:
                        classification = "DEGRADATION_PRODUCT"

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
                        confidence=confidence,
                        regulatory_flags=regulatory,
                        evidence_refs=[{
                            "property": "pathway_source",
                            "value": "literature_review",
                            "source": "AEGIS fallback database",
                            "test_method": "literature_compilation",
                            "date": "2024-01-01",
                            "confidence": confidence,
                        }],
                        pathway=[compound, product],
                        overall_confidence=confidence,
                        litigation_flag=product.upper().replace(" ", "") in litigation_products,
                        is_short_chain_pfas=product.upper() in short_chain_pfas,
                    ))

        summary = result.get("summary", "")
        if not summary:
            if findings:
                summary = f"Analysis of {compound} identified {len(findings)} potential degradation products under the specified conditions."
            else:
                summary = f"No known degradation pathways found for {compound} in the current database."

        return AnalyzeResponse(
            compound_evaluated=result.get("compound_evaluated", compound),
            scenario_context=result.get("scenario_context", scenario or {}),
            pfas_findings=findings,
            summary=summary,
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
