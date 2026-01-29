#!/usr/bin/env python3
"""
Module: risk_models
Purpose: Risk assessment and evidence tracking models for AEGIS.
    Provides EvidenceRow for SWE-013/SWE-033 compliant citation tracking,
    RiskFinding for individual pathway risks, and RiskAssessmentResult
    for complete evaluation outputs.

    Rev History:
        1.0.0 - Initial risk models with evidence traceability

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class EvidenceRow:
    """
    BoundState-compliant evidence citation row (SWE-013/SWE-033 traceability).

    Used to track source attribution for pathway data, satisfying
    compliance requirements for evidence traceability.

    Attributes:
        property: Property being evidenced (e.g., "pfas_formation_pathway")
        value: Measured/reported value
        source: DOI, test report, or literature reference
        test_method: Experimental method (e.g., "literature_review", "analysis")
        date: ISO 8601 date (YYYY-MM-DD)
        confidence: Quality score [0.0, 1.0]
        notes: Additional context
    """

    property: str
    value: Union[float, str]
    source: str
    test_method: str
    date: str
    confidence: float = 1.0
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )
        from datetime import datetime
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(
                f"date must be ISO 8601 (YYYY-MM-DD), got: {self.date}"
            ) from exc

    def to_dict(self) -> Dict[str, Any]:
        """Export evidence row to serializable dictionary."""
        return {
            "property": self.property,
            "value": self.value,
            "source": self.source,
            "test_method": self.test_method,
            "date": self.date,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass
class RiskFinding:
    """
    Individual risk finding from pathway evaluation.

    Represents a single PFAS formation pathway with its associated
    risk classification, conditions, and regulatory context.
    """

    product: str
    screening_classification: str
    path_conditions: List[Dict[str, Any]]
    confidence: float
    regulatory_flags: List[str]
    evidence_refs: List[Dict[str, Any]]
    is_short_chain_pfas: bool = False
    litigation_flag: bool = False
    disposal_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Export finding to serializable dictionary."""
        return {
            "product": self.product,
            "screening_classification": self.screening_classification,
            "conditions_where_it_forms": self.path_conditions,
            "confidence": self.confidence,
            "regulatory_flags": self.regulatory_flags,
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class RiskAssessmentResult:
    """
    Complete risk assessment result from AEGIS evaluation.
    """

    compound_evaluated: str
    scenario_context: Dict[str, Any]
    pfas_findings: List[RiskFinding]
    summary: str
    disclaimer: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Export result to serializable dictionary."""
        return {
            "compound_evaluated": self.compound_evaluated,
            "scenario_context": self.scenario_context,
            "pfas_findings": [f.to_dict() for f in self.pfas_findings],
            "summary": self.summary,
            "disclaimer": self.disclaimer,
        }

    @property
    def has_findings(self) -> bool:
        """Return True if any PFAS findings were identified."""
        return len(self.pfas_findings) > 0

    @property
    def highest_risk_finding(self) -> Optional[RiskFinding]:
        """Return the finding with highest regulatory concern."""
        if not self.pfas_findings:
            return None
        # Prioritize: litigation > regulated > short-chain > other
        for finding in self.pfas_findings:
            if finding.litigation_flag:
                return finding
        for finding in self.pfas_findings:
            if finding.regulatory_flags:
                return finding
        for finding in self.pfas_findings:
            if finding.is_short_chain_pfas:
                return finding
        return self.pfas_findings[0]
