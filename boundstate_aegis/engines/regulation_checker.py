#!/usr/bin/env python3
"""
Module: regulation_checker
Purpose: Regulation checker for PFAS compound regulatory status.
    Provides check_regulatory_status() to evaluate compound regulation
    across US EPA, EU REACH, and state-level jurisdictions with
    litigation exposure tracking.

    Rev History:
        1.0.0 - Initial regulation checker with multi-jurisdiction support

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from boundstate_aegis.knowledge.graph_builder import PFASKnowledgeGraph

from boundstate_aegis.models.regulatory_models import (
    Jurisdiction,
    RegulatoryStatus,
    LitigationStatus,
)


# Known regulatory programs by jurisdiction
REGULATORY_PROGRAMS: Dict[Jurisdiction, List[str]] = {
    Jurisdiction.US_EPA: [
        "EPA PFAS Strategic Roadmap",
        "TSCA §8 PFAS Reporting",
        "CWA/SDWA PFAS Limits",
        "EPA Method 537.1/533/8327",
    ],
    Jurisdiction.US_STATE: [
        "California drinking water monitoring",
        "State PFAS regulations",
    ],
    Jurisdiction.EU_REACH: [
        "REACH Annex XV PFAS restriction proposal",
        "EU POPs Regulation",
    ],
    Jurisdiction.EU_OTHER: [
        "EU atmospheric monitoring programs",
    ],
}


def check_regulatory_status(
    compound_name: str,
    graph: Optional["PFASKnowledgeGraph"] = None,
    node_attrs: Optional[Dict[str, Any]] = None,
) -> RegulatoryStatus:
    """
    Check regulatory status for a compound.

    Args:
        compound_name: Name of the compound to check.
        graph: Optional knowledge graph to query for node attributes.
        node_attrs: Optional pre-fetched node attributes.

    Returns:
        RegulatoryStatus with flags and affected jurisdictions.
    """
    if node_attrs is None and graph is not None:
        node_attrs = graph.get_node_attributes(compound_name)
    elif node_attrs is None:
        node_attrs = {}

    regulated_in = node_attrs.get("regulated_in", [])
    if isinstance(regulated_in, str):
        regulated_in = [regulated_in]

    litigation_flag = bool(node_attrs.get("litigation_flag", False))
    is_pfas = bool(node_attrs.get("is_pfas", False))
    is_short_chain = bool(node_attrs.get("is_short_chain_pfas", False))

    # Determine affected jurisdictions
    jurisdictions: List[Jurisdiction] = []
    for reg in regulated_in:
        reg_lower = reg.lower()
        if "epa" in reg_lower or "tsca" in reg_lower or "cwa" in reg_lower:
            if Jurisdiction.US_EPA not in jurisdictions:
                jurisdictions.append(Jurisdiction.US_EPA)
        if "california" in reg_lower or "state" in reg_lower:
            if Jurisdiction.US_STATE not in jurisdictions:
                jurisdictions.append(Jurisdiction.US_STATE)
        if "reach" in reg_lower or "pops" in reg_lower:
            if Jurisdiction.EU_REACH not in jurisdictions:
                jurisdictions.append(Jurisdiction.EU_REACH)
        if "eu" in reg_lower and "reach" not in reg_lower and "pops" not in reg_lower:
            if Jurisdiction.EU_OTHER not in jurisdictions:
                jurisdictions.append(Jurisdiction.EU_OTHER)

    # Determine litigation status
    if litigation_flag:
        litigation_status = LitigationStatus.ACTIVE
    else:
        litigation_status = LitigationStatus.NONE

    return RegulatoryStatus(
        compound_name=compound_name,
        is_pfas=is_pfas,
        is_short_chain_pfas=is_short_chain,
        regulated_in=regulated_in,
        jurisdictions=jurisdictions,
        litigation_status=litigation_status,
    )


def get_regulatory_summary(status: RegulatoryStatus) -> str:
    """Generate human-readable regulatory summary."""
    if not status.is_pfas:
        return f"{status.compound_name} is not classified as a PFAS compound."

    parts = [f"{status.compound_name} is a PFAS compound"]

    if status.is_short_chain_pfas:
        parts.append("(short-chain C4-C7)")

    if status.regulated_in:
        parts.append(f"regulated in: {', '.join(status.regulated_in)}")

    if status.litigation_status == LitigationStatus.ACTIVE:
        parts.append("with active litigation")

    return " ".join(parts) + "."
