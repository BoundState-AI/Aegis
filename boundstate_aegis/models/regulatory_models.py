#!/usr/bin/env python3
"""
Module: regulatory_models
Purpose: Regulatory framework models for PFAS compliance and litigation tracking.
    Provides Jurisdiction enum, RegulatoryStatus dataclass for compound
    regulation status, and LitigationRecord for exposure tracking.

    Rev History:
        1.0.0 - Initial regulatory models with jurisdiction enums

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
from enum import Enum


class Jurisdiction(Enum):
    """Regulatory jurisdictions with PFAS requirements."""

    US_EPA = "US EPA"
    US_STATE = "US State"
    EU_REACH = "EU REACH"
    EU_OTHER = "EU Other"
    EU_POPS = "EU POPs Regulation"
    CALIFORNIA = "California"
    NEW_YORK = "New York"
    MICHIGAN = "Michigan"
    INTERNATIONAL = "International"


class LitigationStatus(Enum):
    """Litigation status for PFAS compounds."""

    NONE = "none"
    ACTIVE = "active"
    SETTLED = "settled"
    PENDING = "pending"


@dataclass
class RegulatoryStatus:
    """
    Regulatory status of a PFAS compound.

    Attributes:
        compound_name: Name of the PFAS compound
        is_pfas: Whether compound is classified as PFAS
        is_short_chain_pfas: Whether compound is short-chain (C4-C7)
        regulated_in: List of regulatory programs
        jurisdictions: List of affected jurisdictions
        litigation_status: Litigation exposure status
    """

    compound_name: str
    is_pfas: bool = False
    is_short_chain_pfas: bool = False
    regulated_in: List[str] = field(default_factory=list)
    jurisdictions: List[Jurisdiction] = field(default_factory=list)
    litigation_status: LitigationStatus = LitigationStatus.NONE

    def is_regulated(self) -> bool:
        """Check if compound is regulated in any jurisdiction."""
        return len(self.regulated_in) > 0 or len(self.jurisdictions) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Export to serializable dictionary."""
        return {
            "compound_name": self.compound_name,
            "is_pfas": self.is_pfas,
            "is_short_chain_pfas": self.is_short_chain_pfas,
            "regulated_in": self.regulated_in,
            "jurisdictions": [j.value for j in self.jurisdictions],
            "litigation_status": self.litigation_status.value,
        }


@dataclass
class LitigationRecord:
    """
    Litigation exposure tracking for a PFAS compound.
    """

    compound_name: str
    case_type: str  # e.g., "class_action", "enforcement", "regulatory"
    jurisdiction: str
    status: LitigationStatus
    estimated_exposure: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Export to serializable dictionary."""
        return {
            "compound_name": self.compound_name,
            "case_type": self.case_type,
            "jurisdiction": self.jurisdiction,
            "status": self.status.value,
            "estimated_exposure": self.estimated_exposure,
            "notes": self.notes,
        }
