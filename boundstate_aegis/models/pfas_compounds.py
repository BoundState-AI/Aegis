#!/usr/bin/env python3
"""
Module: pfas_compounds
Purpose: PFAS compound model definitions and known endpoint compounds.
    Defines CompoundNode dataclass for chemical compound representation
    with regulatory metadata, and KNOWN_PFAS_ENDPOINTS for graph initialization.

    Rev History:
        1.0.0 - Initial CompoundNode model with regulatory flags

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CompoundNode:
    """
    Representation of a chemical compound with regulatory metadata.

    Attributes:
        name: Canonical compound name (e.g., "PFOA", "FEP", "PTFE")
        is_pfas: Whether this compound is classified as a PFAS
        is_short_chain_pfas: Whether this is a short-chain (C4-C7) PFAS
        cas_number: CAS registry number if known
        aliases: Alternative chemical names
        common_aliases: Common/trade names (e.g., "Teflon")
        litigation_flag: Whether compound is subject to active litigation
        metadata: Additional regulatory and classification data
    """

    name: str
    is_pfas: bool = False
    is_short_chain_pfas: bool = False
    cas_number: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    common_aliases: List[str] = field(default_factory=list)
    litigation_flag: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_all_names(self) -> List[str]:
        """Return all names/aliases for this compound."""
        return list(dict.fromkeys(
            [self.name] + (self.aliases or []) + (self.common_aliases or [])
        ))

    def is_regulated(self) -> bool:
        """Check if compound has any regulatory flags."""
        regulated_in = self.metadata.get("regulated_in", [])
        return bool(regulated_in) or self.litigation_flag


# Known PFAS endpoint compounds for graph initialization
KNOWN_PFAS_ENDPOINTS = [
    CompoundNode(
        name="PFHxA",
        is_pfas=True,
        is_short_chain_pfas=True,
        metadata={
            "pfas_category": "short_chain",
            "regulated_in": [
                "California (drinking water monitoring)",
                "EU (short-chain PFAS restriction proposal)",
            ],
        },
    ),
    CompoundNode(
        name="PFNA",
        is_pfas=True,
        is_short_chain_pfas=True,
        metadata={
            "pfas_category": "short_chain",
            "regulated_in": [
                "EU REACH Annex XV (broad PFAS restriction proposal)",
            ],
        },
    ),
    CompoundNode(
        name="PFOA",
        is_pfas=True,
        is_short_chain_pfas=False,
        litigation_flag=True,
        metadata={
            "pfas_category": "legacy_long_chain",
            "regulated_in": [
                "US EPA (legacy PFAS regulation)",
                "EU POPs Regulation",
            ],
        },
    ),
    CompoundNode(
        name="TFA",
        is_pfas=True,
        is_short_chain_pfas=True,
        metadata={
            "pfas_category": "ultra_short_chain",
            "regulated_in": [
                "EU (atmospheric monitoring programs)",
            ],
        },
    ),
]
