#!/usr/bin/env python3
"""
Core datamodels for AEGIS regulatory monitoring L2-L4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DiffType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    NOISE_ONLY = "noise_only"
    UNCHANGED = "unchanged"


class Classification(str, Enum):
    REGULATORY_ACTION = "regulatory_action"
    ENFORCEMENT = "enforcement"
    TIMELINE_CHANGE = "timeline_change"
    GUIDANCE_UPDATE = "guidance_update"
    CONSULTATION_OPENING = "consultation_opening"
    CONSULTATION_CLOSING = "consultation_closing"
    DATA_UPDATE = "data_update"
    ORGANIZATIONAL = "organizational"
    NOISE = "noise"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOISE = "noise"


class ImpactRating(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class ContentSnapshot:
    source_id: str
    url: str
    label: str
    country: str
    tier: str
    raw_hash: str
    content_hash: str
    extracted_text: str
    captured_at: str
    content_length: int
    extraction_method: str
    content_type: str = ""
    http_status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    normalization_rules_applied: List[str] = field(default_factory=list)
    raw_content_gzip_b64: Optional[str] = None


@dataclass
class EvidenceSpan:
    span_id: str
    text: str
    location: str
    span_type: str  # added | removed | modified


@dataclass
class ContentDiff:
    diff_id: str
    source_id: str
    url: str
    label: str
    country: str
    diff_type: str
    additions: List[EvidenceSpan] = field(default_factory=list)
    removals: List[EvidenceSpan] = field(default_factory=list)
    modifications: List[EvidenceSpan] = field(default_factory=list)
    added_word_count: int = 0
    removed_word_count: int = 0
    keyword_hits: List[str] = field(default_factory=list)
    noise_filtered: bool = False
    raw_diff: str = ""
    summary: str = ""


@dataclass
class TriggerDecision:
    trigger_level3: bool
    reason: str
    priority: str = "low"
    alert_immediately: bool = False


@dataclass
class TriageResult:
    classification: str
    signal_severity: str
    confidence: float
    summary: str
    compounds_affected: List[str] = field(default_factory=list)
    jurisdictions_affected: List[str] = field(default_factory=list)
    action_type: str = ""
    effective_date: Optional[str] = None
    evidence_span_ids: List[str] = field(default_factory=list)
    raw_signal: str = ""
    model_used: str = "heuristic"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactAssessment:
    impact_rating: str
    business_units_affected: List[str]
    exposure_type: str
    financial_exposure: str
    timeline: str
    recommended_actions: List[str]
    cascade_risk: str
    aegis_assertion_update: str
    briefing_summary: str
    reasoning: List[str] = field(default_factory=list)
    model_used: str = "heuristic"
    score_components: Dict[str, float] = field(default_factory=dict)


@dataclass
class RegulatorySignal:
    signal_id: str
    source_url: str
    source_label: str
    country: str
    detected_at: str
    classification: str
    severity: str
    summary: str
    compounds_affected: List[str]
    jurisdictions_affected: List[str]
    action_type: str
    effective_date: Optional[str]
    confidence: float
    raw_signal: str
    diff_id: str
    triage: Dict[str, Any]
    fetch_provenance: str = "direct"
    impact: Optional[Dict[str, Any]] = None
    priority_score: float = 0.0
