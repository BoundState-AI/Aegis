#!/usr/bin/env python3
"""
Module: models
Purpose: AEGIS data models for PFAS compounds, pathways, and risk assessment.
    Provides core dataclasses including CompoundNode, DegradationEdge,
    EvidenceRow, RiskFinding, and regulatory status models.

    Rev History:
        1.0.0 - Initial models package

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from boundstate_aegis.models.pfas_compounds import CompoundNode
from boundstate_aegis.models.degradation_pathways import DegradationEdge
from boundstate_aegis.models.risk_models import EvidenceRow, RiskFinding
from boundstate_aegis.models.regulatory_models import RegulatoryStatus, Jurisdiction

__all__ = [
    "CompoundNode",
    "DegradationEdge",
    "EvidenceRow",
    "RiskFinding",
    "RegulatoryStatus",
    "Jurisdiction",
]
