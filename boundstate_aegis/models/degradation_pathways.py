#!/usr/bin/env python3
"""
Module: degradation_pathways
Purpose: Degradation pathway edge model for PFAS transformation tracking.
    Defines DegradationEdge dataclass representing directed transformation
    edges between compounds with conditions, mechanisms, and evidence citations.

    Rev History:
        1.0.0 - Initial DegradationEdge model with condition tracking

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from boundstate_aegis.models.risk_models import EvidenceRow


@dataclass
class DegradationEdge:
    """
    Directed transformation edge connecting a parent compound to a product.

    Represents a single step in a degradation pathway, with associated
    conditions (temperature, atmosphere) and evidence citations.

    Attributes:
        parent: Source compound name
        child: Product compound name
        mechanism: Transformation mechanism (e.g., "thermal", "UV_photolysis", "hydrolysis")
        min_temp_c: Minimum temperature for pathway activation (°C)
        max_temp_c: Maximum temperature for pathway (°C)
        atmosphere: Atmosphere descriptor (e.g., "air", "oxygen-rich", "inert")
        residence_time_s: Reaction time in seconds
        confidence: Confidence score [0.0, 1.0]
        evidence_refs: List of evidence citations supporting this pathway
    """

    parent: str
    child: str
    mechanism: str
    min_temp_c: Optional[float] = None
    max_temp_c: Optional[float] = None
    atmosphere: Optional[str] = None
    residence_time_s: Optional[float] = None
    confidence: float = 1.0
    evidence_refs: List["EvidenceRow"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0; got {self.confidence}"
            )

    def conditions_summary(self) -> str:
        """Return human-readable summary of pathway conditions."""
        parts = []
        if self.min_temp_c is not None or self.max_temp_c is not None:
            temp_str = ""
            if self.min_temp_c is not None and self.max_temp_c is not None:
                temp_str = f"{self.min_temp_c:.0f}-{self.max_temp_c:.0f}°C"
            elif self.min_temp_c is not None:
                temp_str = f"≥{self.min_temp_c:.0f}°C"
            elif self.max_temp_c is not None:
                temp_str = f"≤{self.max_temp_c:.0f}°C"
            parts.append(temp_str)
        if self.atmosphere:
            parts.append(self.atmosphere)
        if self.mechanism:
            parts.append(self.mechanism)
        return ", ".join(parts) if parts else "unspecified conditions"

    def to_dict(self) -> dict:
        """Export edge to serializable dictionary."""
        return {
            "parent": self.parent,
            "child": self.child,
            "mechanism": self.mechanism,
            "min_temp_c": self.min_temp_c,
            "max_temp_c": self.max_temp_c,
            "atmosphere": self.atmosphere,
            "residence_time_s": self.residence_time_s,
            "confidence": self.confidence,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
        }
