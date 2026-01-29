#!/usr/bin/env python3
"""
Module: destruction_technology
Purpose: Pydantic models for PFAS destruction technologies.
    Supports the EOL Proof Certificate generator by providing structured
    lookup of destruction options, capabilities, and IP positions.

    Rev History:
        1.0.0 - Initial destruction technology models

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>

"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TechnologyReadinessLevel(IntEnum):
    """NASA Technology Readiness Levels (TRL)."""
    TRL_1_BASIC_PRINCIPLES = 1
    TRL_2_CONCEPT_FORMULATED = 2
    TRL_3_PROOF_OF_CONCEPT = 3
    TRL_4_LAB_VALIDATION = 4
    TRL_5_PILOT_DEMO = 5
    TRL_6_PROTOTYPE_DEMO = 6
    TRL_7_COMMERCIAL_PILOT = 7
    TRL_8_COMMERCIAL = 8
    TRL_9_MATURE = 9


class DestructionCapability(BaseModel):
    """Describes what a technology can effectively destroy."""
    compound_class: str = Field(..., description="Class of compounds (e.g., 'ultra-short-chain PFAS')")
    includes: List[str] = Field(default_factory=list, description="Specific compounds included")
    phase: str = Field(..., description="Matrix phase: aqueous, gas, solid, slurry")
    min_dre: float = Field(..., ge=0.0, le=1.0, description="Minimum Destruction/Removal Efficiency")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Operating conditions")
    notes: Optional[str] = Field(default=None)


class DestructionIneffective(BaseModel):
    """Describes what a technology cannot effectively destroy."""
    compound_class: str
    reason: str
    notes: Optional[str] = None


class EvidenceRef(BaseModel):
    """Reference to supporting evidence."""
    doi: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    citation: Optional[str] = None
    key_finding: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None


class CostEstimate(BaseModel):
    """Cost estimates for a technology."""
    capex_estimate: Optional[str] = None
    opex_estimate: Optional[str] = None
    notes: Optional[str] = None


class ChemoursPosition(BaseModel):
    """Chemours' IP and commercial position relative to a technology."""
    owns_technology: bool = False
    owns_ip: bool = False
    must_license_from: Optional[str] = None
    forced_buyer: bool = False
    location: Optional[str] = None
    limitation: Optional[str] = None
    notes: Optional[str] = None


class DestructionTechnology(BaseModel):
    """
    Complete model for a PFAS destruction technology.

    Used by EOL Proof Certificate generator to recommend destruction
    options and assess Chemours' IP exposure.
    """
    id: str = Field(..., description="Unique technology identifier")
    name: str = Field(..., description="Full technology name")
    acronym: Optional[str] = Field(default=None, description="Common acronym (e.g., HALT, SCWO)")
    mechanism: str = Field(..., description="Destruction mechanism")

    # Developers and operators
    developer: Optional[str] = None
    developers: List[str] = Field(default_factory=list)
    commercial_operator: Optional[str] = None
    commercial_operators: List[str] = Field(default_factory=list)
    ip_holder: Optional[str] = None

    # Maturity
    trl: int = Field(..., ge=1, le=9, description="Technology Readiness Level (1-9)")

    # Capabilities
    effective_for: List[DestructionCapability] = Field(default_factory=list)
    ineffective_for: List[DestructionIneffective] = Field(default_factory=list)

    # Products and byproducts
    products: Optional[Dict[str, Any]] = None

    # Challenges
    challenges: List[str] = Field(default_factory=list)

    # Evidence
    evidence: Optional[Dict[str, Any]] = None

    # Costs
    costs: Optional[CostEstimate] = None

    # Chemours position
    chemours_position: Optional[ChemoursPosition] = None

    def can_destroy(self, compound: str, phase: str = "aqueous") -> bool:
        """Check if technology can destroy a specific compound in given phase."""
        compound_upper = compound.upper()
        for cap in self.effective_for:
            if cap.phase != phase:
                continue
            # Check if compound is in includes list
            if compound_upper in [c.upper() for c in cap.includes]:
                return True
            # Check if compound class matches
            if compound_upper in cap.compound_class.upper():
                return True
        return False

    def get_dre_for(self, compound: str, phase: str = "aqueous") -> Optional[float]:
        """Get destruction/removal efficiency for a compound."""
        compound_upper = compound.upper()
        for cap in self.effective_for:
            if cap.phase != phase:
                continue
            if compound_upper in [c.upper() for c in cap.includes]:
                return cap.min_dre
            if compound_upper in cap.compound_class.upper():
                return cap.min_dre
        return None

    def get_conditions_for(self, compound: str, phase: str = "aqueous") -> Optional[Dict[str, Any]]:
        """Get operating conditions for destroying a compound."""
        compound_upper = compound.upper()
        for cap in self.effective_for:
            if cap.phase != phase:
                continue
            if compound_upper in [c.upper() for c in cap.includes]:
                return cap.conditions
            if compound_upper in cap.compound_class.upper():
                return cap.conditions
        return None

    def is_ineffective_for(self, compound: str) -> Optional[str]:
        """Check if technology is ineffective for a compound, return reason if so."""
        compound_upper = compound.upper()
        for ineff in self.ineffective_for:
            if compound_upper in ineff.compound_class.upper():
                return ineff.reason
        return None

    def chemours_must_license(self) -> bool:
        """Check if Chemours must license this technology."""
        if self.chemours_position is None:
            return True  # Assume must license if unknown
        return not self.chemours_position.owns_technology and not self.chemours_position.owns_ip

    def to_summary(self) -> Dict[str, Any]:
        """Generate summary dict for EOL certificate."""
        return {
            "technology": self.name,
            "acronym": self.acronym,
            "trl": self.trl,
            "mechanism": self.mechanism,
            "commercial_operators": self.commercial_operators or ([self.commercial_operator] if self.commercial_operator else []),
            "ip_holder": self.ip_holder,
            "chemours_owns": self.chemours_position.owns_technology if self.chemours_position else False,
            "chemours_must_license": self.chemours_must_license(),
            "forced_buyer": self.chemours_position.forced_buyer if self.chemours_position else True,
        }


class TechnologyRecommendation(BaseModel):
    """Recommendation for which technology to use for a compound."""
    compound: str
    phase: str = "aqueous"
    recommended_technology: str
    recommendation_reason: str
    dre: Optional[float] = None
    conditions: Optional[Dict[str, Any]] = None
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    not_viable: List[Dict[str, str]] = Field(default_factory=list)
    chemours_gap: Optional[str] = None
