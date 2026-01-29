#!/usr/bin/env python3
"""
Module: scoring_engine
Purpose: Scoring engine for PFAS pathway risk calculations.
    Provides ScoreResult dataclass and calculate_pathway_score()
    for quantifying degradation pathway risk based on confidence,
    conditions, and regulatory factors.

    Rev History:
        1.0.0 - Initial scoring engine with pathway risk calculation

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ScoreResult:
    """Result of a pathway score calculation."""

    raw_score: float
    normalized_score: float
    confidence: float
    factors: Dict[str, float]


def calculate_pathway_score(
    path_conditions: List[Dict[str, Any]],
    regulatory_flags: List[str],
    is_short_chain: bool = False,
    litigation_flag: bool = False,
    base_confidence: float = 1.0,
) -> ScoreResult:
    """
    Calculate a composite risk score for a pathway.

    Args:
        path_conditions: List of condition dicts from pathway traversal.
        regulatory_flags: List of regulatory jurisdictions/programs.
        is_short_chain: Whether the endpoint is a short-chain PFAS.
        litigation_flag: Whether compound is under active litigation.
        base_confidence: Starting confidence value from pathway.

    Returns:
        ScoreResult with raw, normalized scores and contributing factors.
    """
    factors: Dict[str, float] = {}

    # Regulatory weight
    reg_weight = min(len(regulatory_flags) * 0.15, 0.45)
    factors["regulatory"] = reg_weight

    # Litigation weight
    lit_weight = 0.3 if litigation_flag else 0.0
    factors["litigation"] = lit_weight

    # Short-chain mobility weight
    sc_weight = 0.2 if is_short_chain else 0.0
    factors["short_chain"] = sc_weight

    # Pathway complexity (fewer steps = higher concern)
    step_count = len(path_conditions) if path_conditions else 1
    complexity_weight = max(0.0, 0.3 - (step_count - 1) * 0.1)
    factors["complexity"] = complexity_weight

    raw_score = sum(factors.values())
    normalized_score = min(1.0, raw_score)

    return ScoreResult(
        raw_score=raw_score,
        normalized_score=normalized_score,
        confidence=base_confidence,
        factors=factors,
    )


def aggregate_scores(scores: List[ScoreResult]) -> Optional[ScoreResult]:
    """
    Aggregate multiple pathway scores into a single compound-level score.

    Uses maximum normalized score with confidence-weighted averaging.
    """
    if not scores:
        return None

    max_score = max(s.normalized_score for s in scores)
    avg_confidence = sum(s.confidence for s in scores) / len(scores)

    combined_factors: Dict[str, float] = {}
    for score in scores:
        for key, val in score.factors.items():
            combined_factors[key] = max(combined_factors.get(key, 0.0), val)

    return ScoreResult(
        raw_score=max_score,
        normalized_score=max_score,
        confidence=avg_confidence,
        factors=combined_factors,
    )
