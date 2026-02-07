#!/usr/bin/env python3
"""
Module: taxonomy
Purpose: Shared endpoint taxonomy and classification logic used by both
    Tier 1 and Tier 2 engines. Single source of truth for endpoint bucket
    definitions and classification heuristics.

    Rev History:
        1.0.0 - Extracted from tier1_engine.py and tier2_substructure_engine.py

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

from typing import Dict, List


# =============================================================================
# ENDPOINT TAXONOMY
# =============================================================================

ENDPOINT_TAXONOMY: Dict[str, List[str]] = {
    "long_chain_acids": [
        "PFOA", "PFNA", "PFDA", "PFUnDA", "PFDoDA",
        "perfluorooctanoic acid",
    ],
    "short_chain_acids": [
        "TFA", "PFBA", "PFPeA", "PFHxA", "PFHpA",
        "trifluoroacetic acid",
    ],
    "sulfonates": [
        "PFOS", "PFHxS", "PFBS",
        "perfluorooctane sulfonic acid",
    ],
    "fluorotelomers": [
        "6:2 FTOH", "8:2 FTOH", "4:2 FTOH", "10:2 FTOH",
        "6:2 FTCA", "8:2 FTCA",
    ],
    "gases": ["HF", "COF2", "CF4", "CO2", "F2", "carbonyl fluoride"],
    "benign": ["H2O", "CO2", "fluoride", "F-", "acetic acid", "formic acid"],
    "radicals": [],
}


def classify_endpoint(product_name: str) -> str:
    """Classify a product into an endpoint bucket."""
    name_lower = product_name.lower()

    for category, members in ENDPOINT_TAXONOMY.items():
        for member in members:
            if member.lower() in name_lower or name_lower in member.lower():
                return category

    # Heuristics for unclassified
    if "radical" in name_lower or "\u2022" in product_name:
        return "radicals"
    if "pfoa" in name_lower or "perfluorooctan" in name_lower:
        return "long_chain_acids"
    if "pfos" in name_lower or "sulfon" in name_lower:
        return "sulfonates"
    if "ftoh" in name_lower or "fluorotelomer" in name_lower:
        return "fluorotelomers"

    return "other"
