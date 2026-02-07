#!/usr/bin/env python3
"""
Module: reports_route
Purpose: Executive reports API endpoints for material-specific PFAS reports.
    Provides /api/v1/reports/* endpoints for the ExecutiveReports UI.
    Generates reports from knowledge graph and evidence databases.

    Rev History:
        1.0.0 - Initial executive reports routes

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
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from boundstate_aegis.knowledge.graph_builder import build_graph, PFASKnowledgeGraph

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for knowledge graph
_graph_cache: Optional[PFASKnowledgeGraph] = None


def get_graph() -> PFASKnowledgeGraph:
    """Get or build knowledge graph (cached)."""
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = build_graph(load_from_data_dir=True)
        logger.info(f"Built knowledge graph with {len(_graph_cache.compounds)} compounds")
    return _graph_cache


def _get_degradation_products(graph: PFASKnowledgeGraph, material: str) -> List[Dict[str, Any]]:
    """Get degradation products for a material from V2 curated database."""
    # Import V2 database (same source as Fate Explorer)
    try:
        from boundstate_aegis.api.routes.fate_route import get_pfas_database
        database = get_pfas_database()
    except ImportError:
        logger.warning("Could not import V2 PFAS database, falling back to graph")
        return _get_degradation_products_from_graph(graph, material)

    products = []
    mat_upper = material.upper()

    # Look up in V2 curated database
    parent_data = database.get(mat_upper)
    if not parent_data:
        return products

    # Extract degradation products from V2 format
    for product in parent_data.get("degradation_products", []):
        # Parse temp_range string (e.g., "400-600°C" or "~500°C")
        temp_range = product.get("temp_range", "N/A")
        min_temp = None
        max_temp = None
        if temp_range and temp_range != "N/A":
            temp_str = temp_range.replace("°C", "").strip()
            if "-" in temp_str:
                parts = temp_str.split("-")
                try:
                    min_temp = float(parts[0])
                    max_temp = float(parts[1])
                except (ValueError, IndexError):
                    pass
            elif temp_str.startswith("~"):
                try:
                    min_temp = max_temp = float(temp_str[1:])
                except ValueError:
                    pass

        products.append({
            "product": product.get("child", "Unknown"),
            "mechanism": product.get("mechanism", "thermal"),
            "min_temp_c": min_temp,
            "max_temp_c": max_temp,
            "confidence": product.get("confidence", 0.8),
            "atmosphere": product.get("atmosphere", "air"),
        })

    return products


def _get_degradation_products_from_graph(graph: PFASKnowledgeGraph, material: str) -> List[Dict[str, Any]]:
    """Fallback: Get degradation products from legacy NetworkX graph."""
    products = []
    mat_upper = material.upper()

    if mat_upper not in graph.graph:
        return products

    for successor in graph.graph.successors(mat_upper):
        edge_data = graph.graph.get_edge_data(mat_upper, successor)
        if edge_data:
            for key, data in edge_data.items():
                products.append({
                    "product": successor,
                    "mechanism": data.get("mechanism", "thermal"),
                    "min_temp_c": data.get("min_temp_c"),
                    "max_temp_c": data.get("max_temp_c"),
                    "confidence": data.get("confidence", 1.0),
                    "atmosphere": data.get("atmosphere"),
                })

    return products


def _get_regulatory_status(material: str) -> Dict[str, Any]:
    """Get regulatory status for a material."""
    # Import here to avoid circular imports
    try:
        from boundstate_aegis.api.routes.regulatory_v1_route import get_regulatory_database
        database = get_regulatory_database()
        return database.get(material.upper(), {})
    except ImportError:
        return {}


def _get_evidence_count(material: str) -> int:
    """Get citation count for a material."""
    try:
        from boundstate_aegis.api.routes.evidence_route import get_evidence_database
        database = get_evidence_database()
        evidence = database.get(material.upper(), [])
        return len(evidence)
    except ImportError:
        return 0


def _format_products_list(products: List[Dict[str, Any]]) -> str:
    """Format degradation products as bullet list."""
    if not products:
        return "No specific degradation pathways documented in the knowledge base."

    lines = []
    for p in products[:8]:  # Limit to 8 products
        product = p["product"]
        mechanism = p.get("mechanism", "thermal")
        min_t = p.get("min_temp_c")
        max_t = p.get("max_temp_c")
        conf = p.get("confidence", 1.0)

        temp_str = ""
        if min_t and max_t:
            temp_str = f" ({int(min_t)}-{int(max_t)}°C)"
        elif min_t:
            temp_str = f" (>{int(min_t)}°C)"
        elif max_t:
            temp_str = f" (<{int(max_t)}°C)"

        conf_label = "high" if conf >= 0.8 else "medium" if conf >= 0.5 else "low"
        lines.append(f"• {product}{temp_str} - {mechanism} [{conf_label} confidence]")

    if len(products) > 8:
        lines.append(f"• ... and {len(products) - 8} more products")

    return "\n".join(lines)


def _determine_risk_level(material: str, reg_status: Dict[str, Any], products: List[Dict[str, Any]]) -> str:
    """Determine overall risk level based on regulatory status and degradation products."""
    risk_level = reg_status.get("risk_level", "UNKNOWN")

    # Check if any products are high-risk PFAS
    high_risk_products = ["PFOA", "PFOS", "GENX", "PFNA", "PFDA", "PFHXS"]
    has_high_risk_product = any(
        p["product"].upper() in high_risk_products for p in products
    )

    if risk_level == "CRITICAL" or reg_status.get("is_regulated"):
        return "HIGH"
    elif risk_level == "HIGH" or has_high_risk_product:
        return "MEDIUM-HIGH"
    elif products:
        return "MEDIUM"
    else:
        return "LOW"


class ReportSection(BaseModel):
    """A section of an executive report."""
    title: str
    content: str
    data: Optional[Dict[str, Any]] = None
    flags: Optional[List[str]] = None
    similar_cases: Optional[List[str]] = None


class ExecutiveReport(BaseModel):
    """Executive report response."""
    title: str
    material: str
    generated: str
    classification: str
    sections: List[ReportSection]
    data_sources: Dict[str, int]


@router.get("/executive", response_model=ExecutiveReport)
async def generate_executive_report(
    material: str = Query(..., description="Material for report"),
    include_litigation: bool = Query(True, description="Include litigation analysis"),
    include_regulatory: bool = Query(True, description="Include regulatory status"),
) -> ExecutiveReport:
    """Generate an executive summary report for a material using knowledge graph data."""
    mat_upper = material.upper()

    # Get data from knowledge graph and databases
    graph = get_graph()
    products = _get_degradation_products(graph, mat_upper)
    reg_status = _get_regulatory_status(mat_upper)
    evidence_count = _get_evidence_count(mat_upper)
    risk_level = _determine_risk_level(mat_upper, reg_status, products)

    # Track data sources
    data_sources = {
        "knowledge_graph_pathways": len(products),
        "evidence_citations": evidence_count,
        "compounds_in_graph": len(graph.compounds),
    }

    sections = []

    # Executive Summary - data-driven
    has_pfas_products = any(
        p["product"].upper() in ["PFOA", "PFOS", "TFA", "GENX", "PFNA", "PFDA", "HF", "COF2"]
        for p in products
    )

    if products:
        exec_content = f"""This report provides a risk assessment for {mat_upper} based on
{len(products)} documented degradation pathways from the AEGIS knowledge base.

Risk Level: {risk_level}
Documented Pathways: {len(products)}
Literature Citations: {evidence_count}

{"Key concern: Degradation products include regulated PFAS compounds." if has_pfas_products else "No direct PFAS endpoint products identified in primary pathways."}"""
    else:
        exec_content = f"""This report provides a risk assessment for {mat_upper}.

Risk Level: {risk_level}
Documented Pathways: None in knowledge base
Literature Citations: {evidence_count}

Note: Limited pathway data available for this material. Manual review recommended."""

    sections.append(ReportSection(
        title="Executive Summary",
        content=exec_content,
        data={"risk_level": risk_level, "pathway_count": len(products)},
    ))

    # Degradation Analysis - from knowledge graph
    products_text = _format_products_list(products)

    if products:
        deg_content = f"""Degradation pathway analysis for {mat_upper} based on {len(products)}
pathways documented in the AEGIS knowledge graph:

{products_text}

These pathways are derived from peer-reviewed literature extraction and curated evidence."""
    else:
        deg_content = f"""No documented degradation pathways for {mat_upper} in the current knowledge base.

This may indicate:
• Material has not been extensively studied
• Degradation products not yet characterized
• Material is stable under typical conditions

Further literature review recommended to characterize potential degradation behavior."""

    sections.append(ReportSection(
        title="Degradation Pathway Analysis",
        content=deg_content,
        data={
            "products": [p["product"] for p in products],
            "mechanisms": list(set(p.get("mechanism", "thermal") for p in products)),
        },
    ))

    # Regulatory Status - from regulatory database
    if include_regulatory:
        flags = reg_status.get("flags", [])
        is_regulated = reg_status.get("is_regulated", False)
        is_pfas = reg_status.get("is_pfas", False)

        if flags:
            flag_lines = []
            for flag in flags[:5]:
                if hasattr(flag, "jurisdiction"):
                    flag_lines.append(f"• {flag.jurisdiction}: {flag.regulation} - {flag.status}")
                elif isinstance(flag, dict):
                    flag_lines.append(f"• {flag.get('jurisdiction', 'Unknown')}: {flag.get('regulation', '')} - {flag.get('status', '')}")
            flag_text = "\n".join(flag_lines)

            reg_content = f"""Regulatory status for {mat_upper}:

PFAS Classification: {"Yes" if is_pfas else "No"}
Currently Regulated: {"Yes" if is_regulated else "No"}

Active Regulatory Flags:
{flag_text}"""
        else:
            reg_content = f"""Regulatory status for {mat_upper}:

PFAS Classification: {"Yes" if is_pfas else "No"}
Currently Regulated: {"Yes" if is_regulated else "No"}

No specific regulatory flags on record. Monitor for:
• EU universal PFAS restriction proposal (2025-2026)
• US EPA CERCLA hazardous substance designations
• State-level PFAS regulations"""

        regulatory_flags = [
            "EU universal PFAS restriction proposal (2025-2026)",
            "EPA CERCLA hazardous substance designation pending",
        ]
        if is_pfas:
            regulatory_flags.insert(0, f"{mat_upper} classified as PFAS compound")
        if is_regulated:
            regulatory_flags.insert(0, f"{mat_upper} subject to existing regulations")

        sections.append(ReportSection(
            title="Regulatory Status",
            content=reg_content,
            flags=regulatory_flags,
        ))

    # Litigation Risk - simplified model with disclaimer
    if include_litigation:
        # High-risk materials for litigation
        high_litigation_materials = ["PFOA", "PFOS", "GENX", "AFFF"]

        if mat_upper in high_litigation_materials:
            lit_content = f"""Litigation risk for {mat_upper} is HIGH based on:

• Active litigation involving this compound
• Class action settlements establishing precedent
• Regulatory designations increasing liability exposure

This material is subject to ongoing multi-district litigation (MDL) and
state-level actions. Consult legal counsel for current exposure assessment.

Note: Litigation risk modeling is in preview. Values shown are estimates."""
            similar = [
                "3M PFAS Settlement ($10.3B, 2023)",
                "DuPont Ohio Settlement ($670M, 2017)",
                "Chemours Environmental ($2.2B, 2022)",
            ]
        elif has_pfas_products:
            lit_content = f"""Litigation risk for {mat_upper} is MODERATE based on:

• No direct {mat_upper} litigation currently active
• Degradation products include regulated PFAS compounds
• Related PFAS litigation trends affecting industry perception

Product liability exposure exists if degradation products cause
documented harm under foreseeable conditions.

Note: Litigation risk modeling is in preview. Values shown are estimates."""
            similar = [
                "Related: 3M PFAS Settlement ($10.3B, 2023)",
            ]
        else:
            lit_content = f"""Litigation risk for {mat_upper} is LOW based on:

• No {mat_upper} litigation identified
• No high-risk PFAS degradation products documented
• Limited regulatory exposure

Monitor for emerging claims as PFAS regulations expand.

Note: Litigation risk modeling is in preview. Values shown are estimates."""
            similar = []

        sections.append(ReportSection(
            title="Litigation Risk Assessment",
            content=lit_content,
            similar_cases=similar if similar else None,
        ))

    # Recommendations - based on actual findings
    if risk_level in ["HIGH", "MEDIUM-HIGH"]:
        rec_content = f"""Based on this assessment for {mat_upper}:

1. IMMEDIATE: Review current use applications for regulatory compliance
2. Implement thermal monitoring to prevent degradation events
3. Document supply chain for PFAS-free certification requirements
4. Allocate litigation reserve for potential claims
5. Engage regulatory counsel for compliance strategy"""
    elif products:
        rec_content = f"""Based on this assessment for {mat_upper}:

1. Maintain thermal process controls to minimize degradation
2. Monitor regulatory developments (EU REACH, US EPA)
3. Document degradation prevention measures
4. Review disposal procedures for emerging requirements
5. Consider lifecycle assessment for product stewardship"""
    else:
        rec_content = f"""Based on this assessment for {mat_upper}:

1. Monitor regulatory developments as PFAS definitions expand
2. Document material composition and supply chain
3. Consider proactive degradation testing if high-temperature applications
4. Maintain awareness of industry litigation trends
5. Review periodically as knowledge base expands"""

    sections.append(ReportSection(
        title="Recommendations",
        content=rec_content,
    ))

    return ExecutiveReport(
        title=f"AEGIS Risk Assessment: {mat_upper}",
        material=mat_upper,
        generated=datetime.utcnow().isoformat(),
        classification="CONFIDENTIAL - ATTORNEY-CLIENT PRIVILEGED",
        sections=sections,
        data_sources=data_sources,
    )
