#!/usr/bin/env python3
"""
Module: regulatory_v1_route
Purpose: Regulatory compliance API endpoints for the RegulatoryCompliance UI.
    Provides /api/v1/regulatory/* endpoints loading regulatory data from
    YAML configuration and EPA databases.

    Rev History:
        1.0.0 - Initial regulatory compliance routes

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

import yaml
from fastapi import APIRouter, Query
from pydantic import BaseModel

from boundstate_aegis.config import REGULATORY_FRAMEWORK_YAML

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for loaded regulatory data
_regulatory_cache: Optional[Dict[str, Any]] = None


def _load_regulatory_framework() -> Dict[str, List[Dict[str, Any]]]:
    """Load regulatory framework from YAML."""
    framework: Dict[str, List[Dict[str, Any]]] = {}

    if REGULATORY_FRAMEWORK_YAML.exists():
        try:
            with open(REGULATORY_FRAMEWORK_YAML, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "regulatory_framework" in data:
                framework = data["regulatory_framework"]
                logger.info(f"Loaded regulatory data for {len(framework)} compounds from YAML")
        except Exception as e:
            logger.error(f"Failed to load regulatory framework: {e}")

    return framework


def get_regulatory_database() -> Dict[str, Dict[str, Any]]:
    """Get or build regulatory database (cached)."""
    global _regulatory_cache
    if _regulatory_cache is None:
        _regulatory_cache = _build_regulatory_database()
    return _regulatory_cache


def _build_regulatory_database() -> Dict[str, Dict[str, Any]]:
    """Build regulatory database from YAML and fallback data."""
    database: Dict[str, Dict[str, Any]] = {}

    # Load from YAML
    yaml_data = _load_regulatory_framework()

    for compound, entries in yaml_data.items():
        compound_upper = compound.upper()
        flags = []

        for entry in entries:
            flags.append(RegulatoryFlag(
                jurisdiction=entry.get("jurisdiction", "Unknown"),
                regulation=entry.get("driver", "General regulation"),
                status=entry.get("status", "Under review"),
                effective_date=entry.get("effective"),
                limit=None,
            ))

        # Determine if regulated based on flags
        is_regulated = any(
            "ban" in (f.status or "").lower() or
            "restrict" in (f.status or "").lower() or
            "enforceable" in (f.status or "").lower()
            for f in flags
        )

        # Determine risk level
        risk_level = "UNKNOWN"
        compound_lower = compound_upper.lower()
        if any(x in compound_lower for x in ["pfoa", "pfos"]):
            risk_level = "CRITICAL"
            is_regulated = True
        elif any(x in compound_lower for x in ["genx", "pfna", "pfda", "pfhxs"]):
            risk_level = "HIGH"
            is_regulated = True
        elif any(x in compound_lower for x in ["pfhxa", "tfa", "pfba"]):
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        database[compound_upper] = {
            "is_pfas": any(x in compound_lower for x in ["pf", "tfa", "genx"]),
            "is_regulated": is_regulated,
            "risk_level": risk_level,
            "flags": flags,
            "degradation_concerns": [],
        }

    # Merge with fallback data (fallback takes precedence for well-defined compounds)
    for name, data in FALLBACK_REGULATORY_DATA.items():
        if name not in database:
            database[name] = data
        else:
            # Merge flags if fallback has more detail
            if data.get("flags") and len(data["flags"]) > len(database[name]["flags"]):
                database[name]["flags"] = data["flags"]
            if data.get("degradation_concerns"):
                database[name]["degradation_concerns"] = data["degradation_concerns"]
            if data.get("risk_level") != "UNKNOWN":
                database[name]["risk_level"] = data["risk_level"]

    logger.info(f"Built regulatory database with {len(database)} compounds")
    return database


class RegulatoryFlag(BaseModel):
    """A regulatory flag for a compound."""
    jurisdiction: str
    regulation: str
    status: str
    effective_date: Optional[str]
    limit: Optional[str]


class RegulatoryStatus(BaseModel):
    """Regulatory status for frontend display."""
    framework: str
    status: str
    limit_ppb: Optional[float] = None
    effective_date: Optional[str] = None
    notes: str


class MaterialRegulatory(BaseModel):
    """Regulatory status for a material."""
    material: str
    is_pfas: bool
    is_regulated: bool
    risk_level: str
    flags: List[RegulatoryFlag]
    degradation_concerns: List[str]


class RegulatoryCheckResponse(BaseModel):
    """Response for regulatory check - matches frontend RegulatoryCheck interface."""
    material: str
    degradation_products: List[str]
    frameworks_checked: int
    compliant: List[RegulatoryStatus]
    non_compliant: List[RegulatoryStatus]
    warnings: List[RegulatoryStatus]
    overall_risk: str


# Fallback regulatory data for well-known compounds
FALLBACK_REGULATORY_DATA = {
    "PTFE": {
        "is_pfas": False,
        "is_regulated": False,
        "risk_level": "LOW",
        "flags": [],
        "degradation_concerns": [
            "Thermal degradation above 400°C produces TFA (trifluoroacetic acid)",
            "HF (hydrogen fluoride) released at high temperatures",
            "Processing residuals may contain PFOA traces in legacy products",
        ],
    },
    "PVDF": {
        "is_pfas": False,
        "is_regulated": False,
        "risk_level": "LOW",
        "flags": [],
        "degradation_concerns": [
            "HF release possible during thermal events",
            "Generally considered safe in normal operating conditions",
        ],
    },
    "PFOA": {
        "is_pfas": True,
        "is_regulated": True,
        "risk_level": "CRITICAL",
        "flags": [
            RegulatoryFlag(
                jurisdiction="US EPA",
                regulation="SDWA - Drinking Water MCL",
                status="Enforceable",
                effective_date="2024-04-10",
                limit="4 ppt",
            ),
            RegulatoryFlag(
                jurisdiction="EU",
                regulation="Stockholm Convention - POPs",
                status="Banned",
                effective_date="2020-07-04",
                limit="Complete ban",
            ),
            RegulatoryFlag(
                jurisdiction="California",
                regulation="Prop 65",
                status="Listed",
                effective_date="2017-11-10",
                limit="Warning required",
            ),
        ],
        "degradation_concerns": [
            "Persistent in environment - no natural degradation pathway",
            "Bioaccumulates in humans and wildlife",
            "Linked to cancer, thyroid disease, immune effects",
        ],
    },
    "PFOS": {
        "is_pfas": True,
        "is_regulated": True,
        "risk_level": "CRITICAL",
        "flags": [
            RegulatoryFlag(
                jurisdiction="US EPA",
                regulation="SDWA - Drinking Water MCL",
                status="Enforceable",
                effective_date="2024-04-10",
                limit="4 ppt",
            ),
            RegulatoryFlag(
                jurisdiction="EU",
                regulation="Stockholm Convention - POPs",
                status="Banned",
                effective_date="2009-05-01",
                limit="Complete ban",
            ),
        ],
        "degradation_concerns": [
            "Extremely persistent - classified as 'forever chemical'",
            "Found in AFFF firefighting foam",
            "Major litigation target",
        ],
    },
    "GenX": {
        "is_pfas": True,
        "is_regulated": True,
        "risk_level": "HIGH",
        "flags": [
            RegulatoryFlag(
                jurisdiction="US EPA",
                regulation="Health Advisory",
                status="Advisory",
                effective_date="2022-06-15",
                limit="10 ppt",
            ),
            RegulatoryFlag(
                jurisdiction="North Carolina",
                regulation="DEQ Health Goal",
                status="Enforceable",
                effective_date="2019-01-01",
                limit="140 ppt",
            ),
        ],
        "degradation_concerns": [
            "PFOA replacement - similar persistence concerns",
            "Active litigation in North Carolina",
            "Potential for broader regulation",
        ],
    },
}

UPCOMING_REGULATIONS = [
    {
        "jurisdiction": "EU",
        "regulation": "Universal PFAS Restriction",
        "status": "Proposed",
        "expected_date": "2025-2026",
        "description": "Comprehensive ban on all PFAS substances",
    },
    {
        "jurisdiction": "US EPA",
        "regulation": "CERCLA Hazardous Substance",
        "status": "Final Rule Expected",
        "expected_date": "2024",
        "description": "PFOA/PFOS designated as hazardous substances",
    },
]


class CascadeItem(BaseModel):
    """A single regulatory cascade event."""
    year: int
    jurisdiction: str
    regulation: str
    impact: str
    probability: float


class CascadePrediction(BaseModel):
    """A cascade prediction for frontend display."""
    status: str
    regulatory_stage: str  # "enacted", "final_pending", "proposed", "under_consideration", "monitoring"
    source: Optional[str] = None  # Citation like "ECHA Proposal 2023-02" or "EPA Final Rule 89 FR 22888"
    affected_products: List[str]


class CascadeResponse(BaseModel):
    """Regulatory cascade forecast response - matches frontend CascadeResponse interface."""
    material: str
    forecast_year: int
    predictions: Dict[str, CascadePrediction]
    recommendation: str


@router.get("/cascade", response_model=CascadeResponse)
async def get_regulatory_cascade(
    material: str = Query(..., description="Material to forecast"),
    forecast_year: int = Query(2025, description="Target year for forecast"),
) -> CascadeResponse:
    """Get regulatory cascade forecast for a material."""
    mat_upper = material.upper()

    # Build predictions dict matching frontend CascadePrediction interface
    predictions: Dict[str, CascadePrediction] = {}

    # EU universal PFAS restriction
    predictions["EU_Universal_PFAS_Ban"] = CascadePrediction(
        status="Comprehensive ban on all PFAS substances under consideration",
        regulatory_stage="proposed",
        source="ECHA PFAS Restriction Proposal, Feb 2023",
        affected_products=["PTFE", "FEP", "PFA", "PVDF", "ETFE"],
    )

    # US EPA CERCLA
    predictions["US_CERCLA_Designation"] = CascadePrediction(
        status="PFOA/PFOS designated as hazardous substances; cleanup liability",
        regulatory_stage="enacted",
        source="EPA Final Rule 89 FR 22888, April 2024",
        affected_products=["PFOA", "PFOS", "GenX"],
    )

    # State-level actions
    predictions["US_State_Product_Bans"] = CascadePrediction(
        status="Multiple states banning PFAS in consumer products",
        regulatory_stage="enacted",
        source="12+ state laws as of 2024",
        affected_products=["All PFAS-containing products"],
    )

    # Material-specific predictions
    if mat_upper in ["PFOA", "PFOS"]:
        predictions["Stockholm_Convention_POPs"] = CascadePrediction(
            status="Complete global phase-out already in effect",
            regulatory_stage="enacted",
            source="Stockholm Convention Annex A/B",
            affected_products=[mat_upper],
        )
    elif mat_upper in ["PTFE", "PVDF", "FEP", "PFA", "ETFE"]:
        predictions["EU_REACH_Restriction"] = CascadePrediction(
            status="Potential use restrictions for fluoropolymers with derogations for critical uses",
            regulatory_stage="proposed",
            source="Part of ECHA universal PFAS proposal",
            affected_products=[mat_upper, "TFA", "HF"],
        )
    elif mat_upper == "GENX":
        predictions["EPA_MCL_Expansion"] = CascadePrediction(
            status="Maximum Contaminant Level set at 10 ppt",
            regulatory_stage="enacted",
            source="EPA NPDWR for PFAS, April 2024",
            affected_products=["GenX", "HFPO-DA"],
        )

    # Generate recommendation based on material type
    database = get_regulatory_database()
    data = database.get(mat_upper, {})
    risk_level = data.get("risk_level", "UNKNOWN")

    if risk_level == "CRITICAL":
        recommendation = f"URGENT: {mat_upper} is subject to existing bans. Immediate phase-out required. Consult legal counsel for compliance strategy."
    elif risk_level == "HIGH":
        recommendation = f"HIGH PRIORITY: {mat_upper} faces significant regulatory pressure. Begin evaluating alternatives and supply chain impacts."
    elif mat_upper in ["PTFE", "PVDF", "FEP", "PFA", "ETFE"]:
        recommendation = f"MONITOR: {mat_upper} may face restrictions by {forecast_year + 1}. Track EU REACH proposal and prepare for potential use restrictions."
    else:
        recommendation = f"LOW RISK: {mat_upper} not currently targeted but monitor regulatory developments as PFAS definition expands."

    return CascadeResponse(
        material=mat_upper,
        forecast_year=forecast_year,
        predictions=predictions,
        recommendation=recommendation,
    )


@router.get("/check", response_model=RegulatoryCheckResponse)
async def check_regulatory(
    material: str = Query(..., description="Material to check"),
    include_degradation: bool = Query(True, description="Include degradation concerns"),
) -> RegulatoryCheckResponse:
    """Check regulatory status for a material - returns format matching frontend RegulatoryCheck interface."""
    mat_upper = material.upper()
    database = get_regulatory_database()

    data = database.get(mat_upper, {
        "is_pfas": False,
        "is_regulated": False,
        "risk_level": "UNKNOWN",
        "flags": [],
        "degradation_concerns": ["No specific data available for this material"],
    })

    flags = data.get("flags", [])

    # Build compliant/non_compliant/warnings lists
    compliant: List[RegulatoryStatus] = []
    non_compliant: List[RegulatoryStatus] = []
    warnings: List[RegulatoryStatus] = []

    # Define frameworks to check
    frameworks = [
        ("US EPA SDWA", "drinking water"),
        ("EU REACH", "chemicals regulation"),
        ("Stockholm Convention", "persistent organic pollutants"),
        ("CA Prop 65", "carcinogens and reproductive toxicants"),
        ("US TSCA", "toxic substances control"),
    ]

    for flag in flags:
        # Parse limit to ppb if available
        limit_ppb = None
        if flag.limit:
            try:
                # Extract numeric value from limit string like "4 ppt"
                limit_str = flag.limit.split()[0]
                limit_val = float(limit_str)
                if "ppt" in flag.limit.lower():
                    limit_ppb = limit_val / 1000
                elif "ppb" in flag.limit.lower():
                    limit_ppb = limit_val
            except (ValueError, IndexError):
                pass

        status_item = RegulatoryStatus(
            framework=f"{flag.jurisdiction} - {flag.regulation}",
            status=flag.status.lower(),
            limit_ppb=limit_ppb,
            effective_date=flag.effective_date,
            notes=f"Limit: {flag.limit}" if flag.limit else f"Status: {flag.status}",
        )

        # Categorize by status
        status_lower = flag.status.lower()
        if status_lower in ["banned", "enforceable", "restricted"]:
            non_compliant.append(status_item)
        elif status_lower in ["advisory", "listed", "monitored"]:
            warnings.append(status_item)
        else:
            compliant.append(status_item)

    # Add compliant frameworks (those not in flags)
    checked_frameworks = {f"{fl.jurisdiction} - {fl.regulation}" for fl in flags}
    for framework_name, framework_desc in frameworks:
        full_name = framework_name
        if full_name not in checked_frameworks:
            # Only add as compliant for materials that aren't regulated
            if not data["is_regulated"]:
                compliant.append(RegulatoryStatus(
                    framework=framework_name,
                    status="compliant",
                    limit_ppb=None,
                    effective_date=None,
                    notes=f"No restrictions under {framework_desc}",
                ))

    # Get degradation products
    degradation_products: List[str] = []
    if include_degradation:
        # Extract product names from degradation concerns
        concerns = data.get("degradation_concerns", [])
        # Common products associated with materials
        product_map = {
            "PTFE": ["TFA", "HF", "CF4", "COF2"],
            "PVDF": ["HF", "VDF"],
            "FEP": ["TFA", "HF", "CF4"],
            "PFA": ["TFA", "HF", "PFOA traces"],
            "PFOA": ["Persistent - no degradation"],
            "PFOS": ["Persistent - no degradation"],
            "GENX": ["HFPO-DA"],
        }
        degradation_products = product_map.get(mat_upper, [])

    # Determine overall risk
    if non_compliant:
        if data.get("risk_level") == "CRITICAL":
            overall_risk = "HIGH"
        else:
            overall_risk = "MEDIUM"
    elif warnings:
        overall_risk = "LOW"
    else:
        overall_risk = "COMPLIANT"

    return RegulatoryCheckResponse(
        material=mat_upper,
        degradation_products=degradation_products,
        frameworks_checked=len(frameworks),
        compliant=compliant,
        non_compliant=non_compliant,
        warnings=warnings,
        overall_risk=overall_risk,
    )
