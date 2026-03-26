#!/usr/bin/env python3
"""
Bouncer and intent classifier for bounded AEGIS chat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from boundstate_aegis.engines.chat.policies import get_page_policy
from boundstate_aegis.models.chat_models import AuthoritativeAnswerSurface, ChatStatus

_INJECTION_PATTERNS = [
    re.compile(r"ignore all previous instructions", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"\byou are now\b", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"pretend you are", re.I),
    re.compile(r"\b(?:drop|delete|insert|update)\s+table\b", re.I),
]

_OFF_TOPIC_PATTERNS = [
    re.compile(r"\b(?:python|javascript|typescript|react|css|sql query|debug my code)\b", re.I),
    re.compile(r"\b(?:weather|restaurant|dating|personal advice|poem|lyrics|joke)\b", re.I),
]

_CAPABILITY_PATTERNS = [
    re.compile(r"\bwhat can (?:this page|you) answer\b", re.I),
    re.compile(r"\bwhat does this page do\b", re.I),
    re.compile(r"\bwhat can you help with\b", re.I),
]

_SUMMARY_PATTERNS = [
    re.compile(r"\bsummar(?:ize|y)\b", re.I),
    re.compile(r"\bwhat(?:'s| is) (?:on|showing on) (?:this page|screen)\b", re.I),
    re.compile(r"\bgive me the current (?:state|summary)\b", re.I),
]

_COMPARE_PATTERNS = [
    re.compile(r"\bcompare\b", re.I),
    re.compile(r"\b(?:difference|versus|vs\.?)\b", re.I),
]

_FILTER_PATTERNS = [
    re.compile(r"\bfilter\b", re.I),
    re.compile(r"\blower(?:ing)?\b", re.I),
    re.compile(r"\braise\b", re.I),
    re.compile(r"\btemperature\b", re.I),
    re.compile(r"\batmosphere\b", re.I),
    re.compile(r"\binclude degradation\b", re.I),
    re.compile(r"\btoggle\b", re.I),
    re.compile(r"\bforecast year\b", re.I),
]


@dataclass
class BouncerOutcome:
    status: ChatStatus
    question_type: str
    handoff_target: Optional[str] = None


def _visible_labels(surface: AuthoritativeAnswerSurface) -> list[str]:
    visible_state = surface.visible_state
    if surface.page_id == "fate-explorer":
        return [
            str(row.get("product") or "").strip().lower()
            for row in visible_state.get("visible_transformations", [])
            if str(row.get("product") or "").strip()
        ]
    if surface.page_id == "regulatory":
        return [
            str(row.get("framework") or "").strip().lower()
            for row in visible_state.get("sample_findings", [])
            if str(row.get("framework") or "").strip()
        ]
    return []


def classify_query(message: str, surface: AuthoritativeAnswerSurface) -> BouncerOutcome:
    text = message.strip()
    lowered = text.lower()

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return BouncerOutcome(
                status=ChatStatus.REFUSED,
                question_type="prompt_injection",
            )

    for pattern in _OFF_TOPIC_PATTERNS:
        if pattern.search(text):
            return BouncerOutcome(
                status=ChatStatus.OUT_OF_SCOPE,
                question_type="off_topic",
            )

    policy = get_page_policy(surface.page_id) or {}
    handoff_keywords = policy.get("handoff_keywords", {})
    for target, keywords in handoff_keywords.items():
        if any(keyword in lowered for keyword in keywords):
            return BouncerOutcome(
                status=ChatStatus.HANDOFF_REQUIRED,
                question_type="handoff",
                handoff_target=target,
            )

    if any(pattern.search(text) for pattern in _CAPABILITY_PATTERNS):
        return BouncerOutcome(ChatStatus.SUPPORTED, "help_capability")

    if any(pattern.search(text) for pattern in _SUMMARY_PATTERNS):
        return BouncerOutcome(ChatStatus.SUPPORTED, "page_summary")

    if any(pattern.search(text) for pattern in _COMPARE_PATTERNS):
        return BouncerOutcome(ChatStatus.SUPPORTED, "compare_visible_results")

    if any(pattern.search(text) for pattern in _FILTER_PATTERNS):
        return BouncerOutcome(ChatStatus.SUPPORTED, "filter_guidance")

    visible_labels = _visible_labels(surface)
    if any(label and label in lowered for label in visible_labels):
        return BouncerOutcome(ChatStatus.SUPPORTED, "explain_visible_result")

    if surface.page_id == "fate-explorer" and re.search(r"\b(?:hazard|pathway|product|regulated)\b", lowered):
        return BouncerOutcome(ChatStatus.SUPPORTED, "explain_visible_result")

    if surface.page_id == "regulatory" and re.search(r"\b(?:risk|compliant|warning|non-?compliant|forecast|framework)\b", lowered):
        return BouncerOutcome(ChatStatus.SUPPORTED, "explain_visible_result")

    if visible_labels:
        return BouncerOutcome(ChatStatus.PARTIAL, "page_summary")

    return BouncerOutcome(ChatStatus.CLARIFICATION_REQUIRED, "clarification")
