#!/usr/bin/env python3
"""
Deterministic demo seed data for regulatory monitor signals.

Purpose:
- Populate SignalStore with realistic signals for demos before cron accumulation.
- Preserve idempotency via stable signal_id values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from .stores import SignalStore


@dataclass(frozen=True)
class SeedSpec:
    signal_id: str
    hours_ago: int
    source_url: str
    source_label: str
    country: str
    classification: str
    severity: str
    summary: str
    compounds_affected: List[str]
    jurisdictions_affected: List[str]
    action_type: str
    effective_date: str | None
    confidence: float
    raw_signal: str
    diff_id: str
    priority_score: float
    impact_rating: str
    timeline: str
    recommended_actions: List[str]
    briefing_summary: str


SEED_SPECS: List[SeedSpec] = [
    SeedSpec(
        signal_id="SEED_DEMO_EU_ECHA_SEAC_001",
        hours_ago=8,
        source_url="https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas",
        source_label="ECHA PFAS Restriction Dossier",
        country="EU",
        classification="timeline_change",
        severity="high",
        summary="SEAC advanced PFAS restriction opinion workflow, narrowing fluoropolymer derogation timelines.",
        compounds_affected=["PTFE", "PVDF", "FEP", "PFA", "ETFE"],
        jurisdictions_affected=["EU"],
        action_type="derogation",
        effective_date="2026-03-01",
        confidence=0.93,
        raw_signal="SEAC workflow update and consultation sequencing for PFAS restriction dossier (late 2025 updates reflected).",
        diff_id="seed_diff_eu_seac_001",
        priority_score=0.84,
        impact_rating="high",
        timeline="90_days",
        recommended_actions=[
            "Prepare legal and regulatory team briefing on SEAC sequencing changes.",
            "Refresh fluoropolymer derogation assumptions in EU scenario models.",
            "Draft Chemours comment strategy for upcoming consultation milestones.",
        ],
        briefing_summary="EU restriction process moved materially forward, tightening decision windows for fluoropolymer exemptions. Chemours should update derogation assumptions and prepare consultation responses.",
    ),
    SeedSpec(
        signal_id="SEED_DEMO_US_EPA_MCL_001",
        hours_ago=16,
        source_url="https://www.epa.gov/newsreleases/epa-announces-it-will-keep-maximum-contaminant-levels-pfoa-pfos",
        source_label="US EPA PFAS Drinking Water Update",
        country="US",
        classification="timeline_change",
        severity="high",
        summary="EPA maintained PFOA/PFOS MCLs while extending compliance horizon and reconsidering PFHxS/PFNA/HFPO-DA elements.",
        compounds_affected=["PFOA", "PFOS", "PFHxS", "PFNA", "HFPO-DA"],
        jurisdictions_affected=["US"],
        action_type="MCL_change",
        effective_date="2031-01-01",
        confidence=0.95,
        raw_signal="May 2025 EPA discontinuity: retained PFOA/PFOS enforceable limits with extended compliance timeline and reconsideration scope for other PFAS metrics.",
        diff_id="seed_diff_us_epa_001",
        priority_score=0.91,
        impact_rating="critical",
        timeline="immediate",
        recommended_actions=[
            "Re-baseline exposure assumptions for GenX/HFPO-DA drinking-water risk.",
            "Coordinate legal and finance review of extended compliance timeline impacts.",
            "Update remediation liability models to reflect mixed-rule posture.",
        ],
        briefing_summary="US drinking-water posture remains binding for PFOA/PFOS but is now bifurcated for other PFAS metrics. GenX-related risk tracking should be treated as actively in flux.",
    ),
    SeedSpec(
        signal_id="SEED_DEMO_AUS_DCCEEW_001",
        hours_ago=28,
        source_url="https://www.dcceew.gov.au/environment/protection/chemicals-management/pfas",
        source_label="Australia DCCEEW PFAS Program",
        country="Australia",
        classification="consultation_opening",
        severity="medium",
        summary="Australian PFAS policy consultation cycle expanded import and use scrutiny for PFOS-linked products.",
        compounds_affected=["PFOS", "AFFF", "PFAS_class"],
        jurisdictions_affected=["Australia"],
        action_type="restriction",
        effective_date=None,
        confidence=0.88,
        raw_signal="DCCEEW consultation channel indicates expanded review pressure on PFOS use and import pathways.",
        diff_id="seed_diff_aus_dcceew_001",
        priority_score=0.66,
        impact_rating="medium",
        timeline="90_days",
        recommended_actions=[
            "Track consultation deadlines and prepare APAC policy brief.",
            "Map PFOS-linked product exposure in ANZ distribution channels.",
        ],
        briefing_summary="Australia signaled further tightening pressure around PFOS pathways. This is a medium-priority APAC signal with potential downstream policy convergence.",
    ),
    SeedSpec(
        signal_id="SEED_DEMO_JPN_MOE_001",
        hours_ago=40,
        source_url="https://www.env.go.jp/en/water/",
        source_label="Japan MOE Water Quality Program",
        country="Japan",
        classification="guidance_update",
        severity="medium",
        summary="Japan water-quality guidance trajectory continues toward tighter PFAS controls, including PFOA/PFOS implementation pathways.",
        compounds_affected=["PFOA", "PFOS", "PFHxS"],
        jurisdictions_affected=["Japan"],
        action_type="guidance",
        effective_date="2026-04-01",
        confidence=0.86,
        raw_signal="Japan MOE publication updates reflect implementation path toward binding PFAS-aligned water quality standards.",
        diff_id="seed_diff_jpn_moe_001",
        priority_score=0.62,
        impact_rating="medium",
        timeline="1_year",
        recommended_actions=[
            "Track finalization dates for Japanese water-standard implementation.",
            "Update APAC compliance matrix for Japan-specific thresholds.",
        ],
        briefing_summary="Japan remains a high-importance APAC jurisdiction with steadily tightening PFAS water standards. Keep compliance timelines synchronized with local implementation dates.",
    ),
]


def build_seed_signals(now: datetime | None = None) -> List[Dict[str, Any]]:
    reference = now or datetime.now(timezone.utc)
    rows: List[Dict[str, Any]] = []
    for spec in SEED_SPECS:
        detected_at = (reference - timedelta(hours=max(1, spec.hours_ago))).replace(microsecond=0).isoformat()
        triage = {
            "classification": spec.classification,
            "signal_severity": spec.severity,
            "confidence": spec.confidence,
            "summary": spec.summary,
            "compounds_affected": spec.compounds_affected,
            "jurisdictions_affected": spec.jurisdictions_affected,
            "action_type": spec.action_type,
            "effective_date": spec.effective_date,
            "evidence_span_ids": [f"{spec.diff_id}_ev1"],
            "raw_signal": spec.raw_signal,
            "model_used": "seeded_demo",
            "metadata": {"seeded": True, "seed_name": spec.signal_id},
        }
        impact = {
            "impact_rating": spec.impact_rating,
            "business_units_affected": ["Fluoropolymers"],
            "exposure_type": "regulatory",
            "financial_exposure": "Potential compliance and liability exposure; quantify with legal/finance review.",
            "timeline": spec.timeline,
            "recommended_actions": spec.recommended_actions,
            "cascade_risk": "Cross-jurisdiction convergence risk present.",
            "aegis_assertion_update": "Flag related assertions for analyst review.",
            "briefing_summary": spec.briefing_summary,
            "reasoning": [
                "Seeded demo signal for pre-cron UX validation.",
                "Structured to match live L2-L4 output contract.",
            ],
            "model_used": "seeded_demo",
            "score_components": {"priority_score": spec.priority_score},
        }
        rows.append(
            {
                "signal_id": spec.signal_id,
                "source_url": spec.source_url,
                "source_label": spec.source_label,
                "country": spec.country,
                "detected_at": detected_at,
                "classification": spec.classification,
                "severity": spec.severity,
                "summary": spec.summary,
                "compounds_affected": spec.compounds_affected,
                "jurisdictions_affected": spec.jurisdictions_affected,
                "action_type": spec.action_type,
                "effective_date": spec.effective_date,
                "confidence": spec.confidence,
                "raw_signal": spec.raw_signal,
                "diff_id": spec.diff_id,
                "triage": triage,
                "impact": impact,
                "fetch_provenance": "seed",
                "priority_score": spec.priority_score,
                "seeded_demo": True,
            }
        )
    return rows


def seed_signal_store(store: SignalStore | None = None, *, now: datetime | None = None) -> Tuple[int, int, List[str]]:
    signal_store = store or SignalStore()
    inserted = 0
    skipped = 0
    inserted_ids: List[str] = []
    for row in build_seed_signals(now=now):
        if signal_store.append(row):
            inserted += 1
            inserted_ids.append(str(row["signal_id"]))
        else:
            skipped += 1
    return inserted, skipped, inserted_ids

