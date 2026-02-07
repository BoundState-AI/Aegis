#!/usr/bin/env python3
"""
Module: portfolio_route
Purpose: Portfolio risk assessment API endpoints for the PortfolioAssessment UI.
    Provides /api/v1/portfolio/* endpoints for multi-material risk scoring.

    Risk scores incorporate regulatory status, compound characteristics, and
    historical litigation patterns. Site-specific factors may affect actual values.

    Rev History:
        1.0.0 - Initial portfolio assessment routes

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

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class MaterialRisk(BaseModel):
    """Risk assessment for a single material."""
    material: str
    risk_score: float
    risk_level: str
    risk_category: str  # Alias for risk_level for frontend
    regulatory_pressure: float
    litigation_exposure: float
    litigation_probability: float  # Alias for frontend
    degradation_products: List[str]
    primary_concern: str
    pfas_count: int = 0
    regulatory_flags: int = 0


class PortfolioAssessment(BaseModel):
    """Portfolio-level risk assessment response."""
    total_materials: int
    overall_risk_score: float
    high_risk_count: int
    total_exposure_usd: float
    risk_distribution: Dict[str, int]
    materials: List[MaterialRisk]
    results: List[MaterialRisk]  # Alias for frontend
    recommendations: List[str]
    executive_summary: str
    methodology_note: str = (
        "Risk assessments incorporate regulatory status, compound characteristics, "
        "and historical patterns. Site-specific factors may affect actual values."
    )


class PortfolioItem(BaseModel):
    """A single portfolio item."""
    material: str
    volume_lbs: int = 10000


class AssessRequest(BaseModel):
    """Request body for portfolio assessment."""
    materials: Optional[List[str]] = None
    items: Optional[List[PortfolioItem]] = None
    include_degradation: bool = True


# Material risk profiles
MATERIAL_PROFILES = {
    "PTFE": {
        "risk_score": 0.45,
        "regulatory_pressure": 0.3,
        "litigation_exposure": 0.2,
        "products": ["TFA", "HF", "CF4", "C2F6", "COF2"],
        "concern": "Thermal degradation produces TFA and HF at elevated temperatures",
    },
    "PVDF": {
        "risk_score": 0.35,
        "regulatory_pressure": 0.25,
        "litigation_exposure": 0.15,
        "products": ["HF", "VDF monomer", "CH2CF2"],
        "concern": "Potential HF release during processing or fire conditions",
    },
    "FEP": {
        "risk_score": 0.50,
        "regulatory_pressure": 0.35,
        "litigation_exposure": 0.25,
        "products": ["TFA", "HF", "CF4", "PFOA traces"],
        "concern": "Historical PFOA processing aid concerns; thermal decomposition",
    },
    "PFA": {
        "risk_score": 0.55,
        "regulatory_pressure": 0.40,
        "litigation_exposure": 0.30,
        "products": ["TFA", "HF", "PFOA traces", "HFPO-DA"],
        "concern": "Processing aid legacy and high-temp degradation products",
    },
    "ETFE": {
        "risk_score": 0.30,
        "regulatory_pressure": 0.20,
        "litigation_exposure": 0.10,
        "products": ["HF", "TFA", "ethylene products"],
        "concern": "Lower risk profile but HF generation at elevated temps",
    },
    "PFOA": {
        "risk_score": 0.95,
        "regulatory_pressure": 0.95,
        "litigation_exposure": 0.90,
        "products": ["Accumulates in environment"],
        "concern": "Banned substance under Stockholm Convention; major litigation target",
    },
    "PFOS": {
        "risk_score": 0.95,
        "regulatory_pressure": 0.95,
        "litigation_exposure": 0.90,
        "products": ["Accumulates in environment"],
        "concern": "Banned substance under Stockholm Convention; AFFF litigation ongoing",
    },
    "GenX": {
        "risk_score": 0.75,
        "regulatory_pressure": 0.70,
        "litigation_exposure": 0.65,
        "products": ["HFPO-DA", "persistent in water"],
        "concern": "EPA health advisory at 10 ppt; active litigation in NC",
    },
}


def get_risk_level(score: float) -> str:
    """Convert risk score to risk level."""
    if score >= 0.8:
        return "CRITICAL"
    elif score >= 0.6:
        return "HIGH"
    elif score >= 0.4:
        return "MEDIUM"
    else:
        return "LOW"


@router.post("/assess", response_model=PortfolioAssessment)
async def assess_portfolio(request: AssessRequest) -> PortfolioAssessment:
    """
    Assess risk across a portfolio of materials.

    Evaluates regulatory pressure, litigation exposure, and
    degradation product concerns for each material.
    """
    # Handle both input formats
    material_list: List[str] = []
    volume_map: Dict[str, int] = {}

    if request.items:
        for item in request.items:
            material_list.append(item.material)
            volume_map[item.material.upper()] = item.volume_lbs
    elif request.materials:
        material_list = request.materials
    else:
        material_list = []

    materials_result = []
    risk_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    total_score = 0.0
    total_exposure = 0.0

    for material in material_list:
        mat_upper = material.upper()
        profile = MATERIAL_PROFILES.get(mat_upper, {
            "risk_score": 0.40,
            "regulatory_pressure": 0.30,
            "litigation_exposure": 0.20,
            "products": ["Unknown degradation products"],
            "concern": "Limited data available for this material",
        })

        risk_score = profile["risk_score"]
        risk_level = get_risk_level(risk_score)
        risk_dist[risk_level] += 1
        total_score += risk_score

        # Calculate exposure based on volume and risk
        volume = volume_map.get(mat_upper, 10000)
        exposure = volume * risk_score * 50  # $50 per lb * risk

        # Count PFAS products
        products = profile["products"]
        pfas_products = [p for p in products if any(
            x in p.upper() for x in ["PFOA", "PFOS", "TFA", "HF", "PFNA", "GENX", "PFAS"]
        )]

        materials_result.append(MaterialRisk(
            material=mat_upper,
            risk_score=risk_score * 100,  # Convert to 0-100 scale for frontend
            risk_level=risk_level,
            risk_category=risk_level,  # Alias
            regulatory_pressure=profile["regulatory_pressure"],
            litigation_exposure=profile["litigation_exposure"],
            litigation_probability=profile["litigation_exposure"],  # Alias
            degradation_products=products if request.include_degradation else [],
            primary_concern=profile["concern"],
            pfas_count=len(pfas_products),
            regulatory_flags=1 if profile["regulatory_pressure"] > 0.5 else 0,
        ))

        total_exposure += exposure

    # Sort by risk score descending
    materials_result.sort(key=lambda m: m.risk_score, reverse=True)

    # Calculate overall score
    num_materials = len(material_list) if material_list else 1
    overall_score = total_score / num_materials

    # Count high risk
    high_risk_count = risk_dist["CRITICAL"] + risk_dist["HIGH"]

    # Generate recommendations
    recommendations = []
    if risk_dist["CRITICAL"] > 0:
        recommendations.append("Immediate action required: Critical risk materials should be prioritized for phase-out or substitution")
    if risk_dist["HIGH"] > 0:
        recommendations.append("Review supply chain alternatives for high-risk materials")
    if any(m.litigation_exposure > 0.5 for m in materials_result):
        recommendations.append("Consider litigation reserve assessment for materials with high exposure")
    if any(m.regulatory_pressure > 0.6 for m in materials_result):
        recommendations.append("Monitor regulatory developments in EU REACH and US EPA for upcoming restrictions")
    if not recommendations:
        recommendations.append("Portfolio risk profile is within acceptable limits; continue monitoring")

    # Build summary paragraphs
    summary_parts = []

    # Overview paragraph
    summary_parts.append(
        f"Assessed {len(material_list)} materials in portfolio."
    )

    # Risk distribution
    if high_risk_count > 0:
        summary_parts.append(
            f"Risk distribution: {risk_dist['CRITICAL']} critical, {risk_dist['HIGH']} high, "
            f"{risk_dist['MEDIUM']} medium, {risk_dist['LOW']} low. "
            f"{high_risk_count} material(s) require priority attention."
        )
    else:
        summary_parts.append(
            f"Risk distribution: {risk_dist['MEDIUM']} medium, {risk_dist['LOW']} low. "
            f"No critical or high-risk materials identified."
        )

    # Recommendations paragraph
    if recommendations:
        summary_parts.append("Recommendations: " + " ".join(recommendations))

    return PortfolioAssessment(
        total_materials=len(material_list),
        overall_risk_score=round(overall_score, 3),
        high_risk_count=high_risk_count,
        total_exposure_usd=total_exposure,  # Kept for API compatibility but not displayed
        risk_distribution=risk_dist,
        materials=materials_result,
        results=materials_result,  # Alias for frontend
        recommendations=recommendations,
        executive_summary="\n\n".join(summary_parts),
    )
