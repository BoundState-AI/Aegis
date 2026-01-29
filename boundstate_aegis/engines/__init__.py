#!/usr/bin/env python3
"""
Module: engines
Purpose: AEGIS risk assessment engines for PFAS pathway evaluation.
    Exports PFASRiskEngine for pathway risk assessment, ScoreResult and
    calculate_pathway_score for scoring, and check_regulatory_status
    for compliance checking.

    Rev History:
        1.0.0 - Initial engines package

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from boundstate_aegis.engines.pfas_risk_engine import PFASRiskEngine
from boundstate_aegis.engines.scoring_engine import ScoreResult, calculate_pathway_score
from boundstate_aegis.engines.regulation_checker import check_regulatory_status

__all__ = [
    "PFASRiskEngine",
    "ScoreResult",
    "calculate_pathway_score",
    "check_regulatory_status",
]

# Tier 1 engine is imported lazily due to RDKit dependency.
# Use: from boundstate_aegis.engines.tier1_engine import AEGISTier1Engine
