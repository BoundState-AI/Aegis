# tqp_rules.py
import re
from typing import List, Tuple

TQP = re.compile(r'\bT\.?Q\.?P\.?\b', re.I)
EXP = re.compile(r'\bTask\s+Order\s+Quality\s+Plan\b', re.I)
CUES = re.compile(r'\b(Task\s*Order|TO\b|sub[- ]?task|deliverable[s]?|verification|plan)\b', re.I)
PHRASES = re.compile(r'\b(per|in|as\s+defined\s+in)\s+the\s+T\.?Q\.?P\.?\b', re.I)

def _windows(text: str, span: Tuple[int, int], size: int = 60) -> str:
    s, e = span
    return text[max(0, s - size): min(len(text), e + size)]

def tqp_score(text: str) -> float:
    """Evidence-based score, no model required."""
    score = 0.0

    # Strong explicit signals
    if EXP.search(text):
        score += 1.0
    if PHRASES.search(text):
        score += 0.8

    # Co-occurrence: TQP near task-order cues
    for m in TQP.finditer(text):
        win = _windows(text, m.span(), 60)
        if CUES.search(win):
            score += 0.6
        else:
            score += 0.2  # isolated TQP is weak but non-zero

    # Light frequency reinforcement, capped
    hits = len(TQP.findall(text)) + len(EXP.findall(text)) + len(PHRASES.findall(text))
    score += min(0.4, 0.05 * max(0, hits - 1))

    return score

POLICY_GUARD = re.compile(r'\b(Task\s*Order|Sub[- ]?Task|TO\b)\b', re.I)

def policy_penalty(text: str) -> float:
    """Demote short, generic policy pages without any task-order cues."""
    wc = len(text.split())
    looks_policy = (wc < 500) and not POLICY_GUARD.search(text)
    return 0.4 if looks_policy else 0.0

def tqp_decision(text: str, base_threshold: float = 0.8) -> bool:
    s = tqp_score(text) - policy_penalty(text)
    return s >= base_threshold

def tqp_evidence(text: str) -> List[str]:
    """Small evidence snippets for logging/QA."""
    ev = []
    for m in TQP.finditer(text):
        ev.append(_windows(text, m.span(), 60))
        if len(ev) >= 3:
            break
    for m in EXP.finditer(text):
        ev.append(_windows(text, m.span(), 60))
        if len(ev) >= 5:
            break
    return ev