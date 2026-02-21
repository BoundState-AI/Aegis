#!/usr/bin/env python3
"""
Normalization and noise filtering for monitor content.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Tuple


HEADER_FOOTER_PATTERNS = [
    r"all rights reserved",
    r"cookie",
    r"privacy policy",
    r"terms of use",
    r"accessibility",
    r"skip to (main )?content",
    r"subscribe to",
    r"back to top",
]

TIMESTAMP_CONTEXT_PATTERNS = [
    r"last updated",
    r"updated on",
    r"page updated",
    r"date modified",
    r"published on",
    r"released on",
]

TIMESTAMP_VALUE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
]


def _strip_control_chars(value: str) -> str:
    value = value.replace("\ufeff", "")
    value = value.replace("\u200b", "")
    value = value.replace("\x00", " ")
    return value


def normalize_text(text: str) -> Tuple[str, List[str]]:
    """
    Normalize extracted text and remove common page-noise patterns.

    Returns tuple(normalized_text, rules_applied).
    """
    rules_applied: List[str] = []
    cleaned = _strip_control_chars(text or "")
    if cleaned != text:
        rules_applied.append("strip_control_chars")

    lines = [ln.strip() for ln in cleaned.splitlines()]
    filtered_lines: List[str] = []

    timestamp_context_re = re.compile("|".join(TIMESTAMP_CONTEXT_PATTERNS), re.IGNORECASE)
    timestamp_value_re = re.compile("|".join(TIMESTAMP_VALUE_PATTERNS), re.IGNORECASE)
    header_footer_re = re.compile("|".join(HEADER_FOOTER_PATTERNS), re.IGNORECASE)

    for ln in lines:
        if not ln:
            filtered_lines.append("")
            continue

        if header_footer_re.search(ln):
            rules_applied.append("remove_header_footer_line")
            continue

        # Drop date-only lines when they look like page metadata, but do not
        # blanket-remove all dates from substantive paragraphs.
        if timestamp_context_re.search(ln) and timestamp_value_re.search(ln):
            rules_applied.append("remove_page_timestamp_line")
            continue

        filtered_lines.append(ln)

    normalized = "\n".join(filtered_lines)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = normalized.strip()
    rules_applied.append("collapse_whitespace")

    # Deduplicate rule names while keeping order.
    deduped_rules: List[str] = []
    for rule in rules_applied:
        if rule not in deduped_rules:
            deduped_rules.append(rule)
    return normalized, deduped_rules


def content_hash(normalized_text: str) -> str:
    return hashlib.sha256((normalized_text or "").encode("utf-8")).hexdigest()
