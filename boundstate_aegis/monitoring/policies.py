#!/usr/bin/env python3
"""
Trigger policies for L3/L4 escalation.
"""

from __future__ import annotations

import re
from typing import List

from .models import ContentDiff, TriggerDecision


CRITICAL_TOKEN_PATTERNS = [
    r"\beffective date\b",
    r"\bppt\b",
    r"\bng/L\b",
    r"\bug/L\b",
    r"\bµg/L\b",
    r"\bderogation\b",
    r"\bexemption\b",
    r"\bban\b",
    r"\bMCL\b",
    r"\bCERCLA\b",
    r"\bconsent order\b",
    r"\bhazardous substance\b",
]


def find_keyword_hits(diff: ContentDiff) -> List[str]:
    scan_text = "\n".join(
        [span.text for span in diff.additions + diff.removals + diff.modifications]
    )
    hits: List[str] = []
    for pattern in CRITICAL_TOKEN_PATTERNS:
        if re.search(pattern, scan_text, flags=re.IGNORECASE):
            hits.append(pattern.replace(r"\b", ""))
    return hits


def evaluate_trigger(
    *,
    diff: ContentDiff,
    tier: str,
    is_new_url: bool,
    status_transition: str | None = None,
) -> TriggerDecision:
    """
    Decide whether to escalate to L3 based on hybrid policy rules.
    """
    if status_transition in {"200_to_404", "new_url", "scope_change"}:
        return TriggerDecision(
            trigger_level3=True,
            reason=f"status transition: {status_transition}",
            priority="high",
            alert_immediately=True,
        )

    if diff.noise_filtered or diff.diff_type == "noise_only":
        return TriggerDecision(
            trigger_level3=False,
            reason="raw hash changed but normalized content unchanged",
            priority="noise",
            alert_immediately=False,
        )

    if is_new_url:
        return TriggerDecision(
            trigger_level3=True,
            reason="new URL detected after baseline",
            priority="high",
            alert_immediately=True,
        )

    if tier.lower() == "primary" and diff.diff_type != "unchanged":
        return TriggerDecision(
            trigger_level3=True,
            reason="primary tier content change",
            priority="high",
            alert_immediately=False,
        )

    if diff.keyword_hits:
        return TriggerDecision(
            trigger_level3=True,
            reason=f"critical token hit(s): {', '.join(diff.keyword_hits[:4])}",
            priority="high",
            alert_immediately=False,
        )

    delta_words = diff.added_word_count + diff.removed_word_count
    if delta_words >= 50:
        return TriggerDecision(
            trigger_level3=True,
            reason=f"substantive word delta {delta_words}",
            priority="medium",
            alert_immediately=False,
        )

    if delta_words > 0:
        return TriggerDecision(
            trigger_level3=False,
            reason=f"minor change {delta_words} words",
            priority="low",
            alert_immediately=False,
        )

    return TriggerDecision(
        trigger_level3=False,
        reason="no substantive change detected",
        priority="noise",
        alert_immediately=False,
    )
