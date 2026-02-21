#!/usr/bin/env python3
"""
Section-aware paragraph diff for extracted content.
"""

from __future__ import annotations

import difflib
import hashlib
from typing import List, Sequence

from .models import ContentDiff, ContentSnapshot, DiffType, EvidenceSpan


def _paragraphs(text: str) -> List[str]:
    raw = [p.strip() for p in (text or "").split("\n\n")]
    return [p for p in raw if p]


def _words(value: str) -> int:
    return len([w for w in (value or "").split() if w.strip()])


def _span(span_type: str, idx: int, text: str, location: str = "body") -> EvidenceSpan:
    span_hash = hashlib.sha1(f"{span_type}:{idx}:{text}".encode("utf-8")).hexdigest()[:12]
    return EvidenceSpan(
        span_id=f"{span_type}-{idx:03d}-{span_hash}",
        text=text,
        location=location,
        span_type=span_type,
    )


def _raw_unified_diff(old_text: str, new_text: str) -> str:
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    lines = difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", lineterm="")
    return "\n".join(lines)


def generate_diff(
    *,
    previous: ContentSnapshot | None,
    current: ContentSnapshot,
    keyword_hits: Sequence[str],
) -> ContentDiff:
    previous_text = previous.extracted_text if previous else ""
    current_text = current.extracted_text
    old_paragraphs = _paragraphs(previous_text)
    new_paragraphs = _paragraphs(current_text)

    matcher = difflib.SequenceMatcher(a=old_paragraphs, b=new_paragraphs)
    additions: List[EvidenceSpan] = []
    removals: List[EvidenceSpan] = []
    modifications: List[EvidenceSpan] = []

    add_idx = 0
    rem_idx = 0
    mod_idx = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            for block in new_paragraphs[j1:j2]:
                add_idx += 1
                additions.append(_span("added", add_idx, block))
        elif tag == "delete":
            for block in old_paragraphs[i1:i2]:
                rem_idx += 1
                removals.append(_span("removed", rem_idx, block))
        elif tag == "replace":
            for block in old_paragraphs[i1:i2]:
                rem_idx += 1
                removals.append(_span("removed", rem_idx, block))
            for block in new_paragraphs[j1:j2]:
                add_idx += 1
                additions.append(_span("added", add_idx, block))
            old_join = " ".join(old_paragraphs[i1:i2]).strip()
            new_join = " ".join(new_paragraphs[j1:j2]).strip()
            if old_join or new_join:
                mod_idx += 1
                text = f"OLD: {old_join}\nNEW: {new_join}".strip()
                modifications.append(_span("modified", mod_idx, text))

    added_word_count = sum(_words(span.text) for span in additions)
    removed_word_count = sum(_words(span.text) for span in removals)

    if previous is None:
        diff_type = DiffType.ADDED.value
    elif previous.content_hash == current.content_hash:
        diff_type = DiffType.NOISE_ONLY.value
    elif additions and removals:
        diff_type = DiffType.MODIFIED.value
    elif additions:
        diff_type = DiffType.ADDED.value
    elif removals:
        diff_type = DiffType.REMOVED.value
    else:
        diff_type = DiffType.UNCHANGED.value

    noise_filtered = previous is not None and previous.raw_hash != current.raw_hash and previous.content_hash == current.content_hash

    summary = f"Added {added_word_count} words, removed {removed_word_count} words"
    diff_id = hashlib.sha1(
        f"{current.source_id}:{current.content_hash}:{added_word_count}:{removed_word_count}".encode("utf-8")
    ).hexdigest()

    return ContentDiff(
        diff_id=diff_id,
        source_id=current.source_id,
        url=current.url,
        label=current.label,
        country=current.country,
        diff_type=diff_type,
        additions=additions,
        removals=removals,
        modifications=modifications,
        added_word_count=added_word_count,
        removed_word_count=removed_word_count,
        keyword_hits=list(keyword_hits),
        noise_filtered=noise_filtered,
        raw_diff=_raw_unified_diff(previous_text, current_text),
        summary=summary,
    )
