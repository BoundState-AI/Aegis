#!/usr/bin/env python3
"""
Module: boundstate_aegis
Purpose: PFAS risk assessment and degradation pathway analysis engine.
    AEGIS evaluates potential PFAS (per- and polyfluoroalkyl substances) formation
    pathways from precursor materials under specified thermal/chemical conditions.
    Given known compounds, pathways, and scenarios, it computes risk assessments
    with regulatory and litigation context.

    This package does NOT auto-detect PFAS in arbitrary text - it requires explicit
    compound/pathway/scenario inputs.

    Rev History:
        1.0.0 - Initial release with pathway tracing and risk assessment

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

__version__ = "1.0.0"

from boundstate_aegis.models.pfas_compounds import CompoundNode
from boundstate_aegis.models.degradation_pathways import DegradationEdge
from boundstate_aegis.models.risk_models import EvidenceRow
from boundstate_aegis.knowledge.graph_builder import PFASKnowledgeGraph, build_graph
from boundstate_aegis.engines.pfas_risk_engine import PFASRiskEngine

__all__ = [
    "__version__",
    "CompoundNode",
    "DegradationEdge",
    "EvidenceRow",
    "PFASKnowledgeGraph",
    "build_graph",
    "PFASRiskEngine",
]
