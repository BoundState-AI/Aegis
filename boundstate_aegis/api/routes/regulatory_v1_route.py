#!/usr/bin/env python3
"""
Module: regulatory_v1_route
Purpose: Regulatory compliance API endpoints for the RegulatoryCompliance UI.
    Provides /api/v1/regulatory/* endpoints loading regulatory data from
    YAML configuration and EPA databases.

    Rev History:
        1.0.0 - Initial regulatory compliance routes

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, Query
from pydantic import BaseModel

from boundstate_aegis.config import (
    APAC_REGULATORY_ASSERTIONS,
    PFAS_FATE_V2_JSON,
    REGULATORY_APAC_MIN_CONFIDENCE,
    REGULATORY_APAC_REQUIRE_PRIMARY_CITATION,
    REGULATORY_STRICT_MODE,
    REGULATORY_FRAMEWORK_YAML,
)
from boundstate_aegis.monitoring.assertions import AssertionStore

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for loaded regulatory data
_regulatory_cache: Optional[Dict[str, Any]] = None

# Cache for fate literature data
_fate_cache: Optional[Dict[str, Any]] = None


# Cache for loaded APAC assertions
_apac_cache: Optional[Dict[str, Any]] = None
_assertion_store: Optional[AssertionStore] = None

FLUOROPOLYMER_MATERIALS = {"PTFE", "PVDF", "FEP", "PFA", "ETFE"}
PFAS_MATERIALS = FLUOROPOLYMER_MATERIALS | {"PFOA", "PFOS", "PFHXS", "PFNA", "GENX", "HFPO-DA", "TFA"}

APAC_COMPOUND_MATCH: Dict[str, List[str]] = {
    "PFOA": ["PFOA", "PFAS_class", "PFAS_and_fluoropolymer"],
    "PFOS": ["PFOS", "PFAS_class", "PFAS_and_fluoropolymer"],
    "PFHXS": ["PFHxS", "PFAS_class"],
    "GENX": ["PFAS_class"],
    "TFA": ["PFAS_class"],
    "PFNA": ["PFAS_class"],
    "PFDA": ["PFAS_class"],
    "PTFE": ["fluoropolymer", "PFAS_and_fluoropolymer"],
    "PVDF": ["fluoropolymer", "PFAS_and_fluoropolymer"],
    "FEP": ["fluoropolymer", "PFAS_and_fluoropolymer"],
    "PFA": ["fluoropolymer", "PFAS_and_fluoropolymer"],
    "ETFE": ["fluoropolymer", "PFAS_and_fluoropolymer"],
}

APAC_STATUS_MAP: Dict[str, str] = {
    "enforced": "enforceable",
    "guidance": "advisory",
    "consultation": "advisory",
    "proposed": "monitored",
    "monitoring": "monitored",
    "unverified": "monitored",
}

APAC_COUNTRY_MAP: Dict[str, str] = {
    "JPN": "Japan",
    "KOR": "South Korea",
    "CHN": "China",
    "AUS": "Australia",
    "SGP": "Singapore",
    "TWN": "Taiwan",
    "IND": "India",
    "APAC": "APAC",
}

ASSERTION_PREFIX_COUNTRY_MAP: Dict[str, str] = {
    **APAC_COUNTRY_MAP,
    "US": "United States",
    "USA": "United States",
    "EU": "European Union",
    "UK": "United Kingdom",
    "CAN": "Canada",
    "DEU": "Germany",
    "DNK": "Denmark",
    "NOR": "Norway",
    "SWE": "Sweden",
    "NLD": "Netherlands",
    "INTL": "International",
    "WHO": "WHO",
    "OECD": "OECD",
}

CASCADE_STAGE_ORDER = {
    "enacted": 0,
    "final_pending": 1,
    "proposed": 2,
    "under_consideration": 3,
    "monitoring": 4,
}


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    value = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            if fmt == "%Y":
                return date(parsed.year, 12, 31)
            if fmt == "%Y-%m":
                return date(parsed.year, parsed.month, 28)
            return parsed
        except ValueError:
            continue
    return None


def _get_assertion_store() -> AssertionStore:
    global _assertion_store
    if _assertion_store is None:
        _assertion_store = AssertionStore()
        _assertion_store.ensure_bootstrapped()
    return _assertion_store


def _is_past_date(date_str: Optional[str]) -> bool:
    parsed = _parse_date(date_str)
    if not parsed:
        return False
    return parsed <= date.today()


def _normalize_framework_status(raw_status: str) -> str:
    status = (raw_status or "").lower()
    if any(token in status for token in ("banned", "ban", "prohibit")):
        return "banned"
    if any(token in status for token in ("enforceable", "enforced", "binding", "restricted")):
        return "enforceable"
    if any(token in status for token in ("advisory", "guideline", "listed")):
        return "advisory"
    if any(token in status for token in ("proposed", "draft", "consultation", "monitor", "pending", "under discussion")):
        return "monitored"
    return "monitored"


def _load_apac_assertions() -> List[Dict[str, Any]]:
    global _apac_cache
    if _apac_cache is None:
        if APAC_REGULATORY_ASSERTIONS.exists():
            try:
                with open(APAC_REGULATORY_ASSERTIONS, encoding="utf-8") as f:
                    _apac_cache = yaml.safe_load(f) or {}
                assertions = (_apac_cache or {}).get("assertions", [])
                logger.info("Loaded %d APAC regulatory assertions", len(assertions))
            except Exception as e:
                logger.error("Failed to load APAC assertions: %s", e)
                _apac_cache = {}
        else:
            logger.warning("APAC assertions file not found: %s", APAC_REGULATORY_ASSERTIONS)
            _apac_cache = {}
    return (_apac_cache or {}).get("assertions", [])


def _get_apac_trajectory() -> Dict[str, Dict[str, Any]]:
    if _apac_cache is None:
        _load_apac_assertions()
    return (_apac_cache or {}).get("regulatory_trajectory", {}) or {}


def _derive_country(assertion_id: str) -> str:
    prefix = assertion_id.split("_", 1)[0].upper() if assertion_id else "APAC"
    return APAC_COUNTRY_MAP.get(prefix, "APAC")


def _assertion_matches_material(assertion: Dict[str, Any], material: Optional[str]) -> bool:
    if not material:
        return True
    mat_upper = material.upper()
    compound_class = assertion.get("compound_class")
    match_classes = APAC_COMPOUND_MATCH.get(mat_upper)
    if match_classes:
        return compound_class in match_classes
    return (assertion.get("id", "").upper().startswith("APAC_"))


def _adjust_apac_confidence(assertion: Dict[str, Any]) -> float:
    confidence = float(assertion.get("confidence", 0.0) or 0.0)
    citations = assertion.get("citations", []) or []
    if citations:
        all_secondary = all(c.get("tier", "secondary") == "secondary" for c in citations)
        if all_secondary and confidence >= 0.90:
            logger.warning(
                "APAC confidence capped at 0.89 (secondary-only citations): %s",
                assertion.get("id", "unknown"),
            )
            confidence = 0.89
    return confidence


def _normalize_apac_status(assertion: Dict[str, Any], confidence: float) -> tuple[str, str]:
    raw_status = (assertion.get("status") or "monitoring").lower()
    if confidence < 0.70:
        return "monitored", "unverified"

    dates = assertion.get("dates", {}) or {}
    effective = dates.get("effective") or dates.get("finalized")

    if raw_status == "finalized":
        if _is_past_date(effective):
            return "enforceable", raw_status
        return "advisory", raw_status

    return APAC_STATUS_MAP.get(raw_status, "monitored"), raw_status


def _get_apac_citation_tier(assertion: Dict[str, Any]) -> str:
    citations = assertion.get("citations", []) or []
    if citations and any(c.get("tier") == "primary" for c in citations):
        return "primary"
    return "secondary"


def _passes_apac_quality_gate(
    *,
    confidence: float,
    raw_status: str,
    citation_tier: str,
    strict_mode: bool,
    min_confidence: float,
    require_primary_citation: bool,
) -> bool:
    if confidence < min_confidence:
        return False
    if strict_mode and raw_status == "unverified":
        return False
    if require_primary_citation and citation_tier != "primary":
        # Production rule: enacted/finalized guidance must cite a primary source.
        # Secondary-only signals are allowed for monitoring/proposed states so
        # we do not create regional blind spots while evidence is being upgraded.
        if raw_status in {"enforced", "finalized", "guidance"}:
            return False
    return True


def _get_apac_assertion_summaries(
    material: Optional[str],
    *,
    strict_mode: bool = REGULATORY_STRICT_MODE,
    min_confidence: float = REGULATORY_APAC_MIN_CONFIDENCE,
    require_primary_citation: bool = REGULATORY_APAC_REQUIRE_PRIMARY_CITATION,
) -> List["APACAssertionSummary"]:
    summaries: List[APACAssertionSummary] = []
    for assertion in _load_apac_assertions():
        if not _assertion_matches_material(assertion, material):
            continue

        confidence = _adjust_apac_confidence(assertion)
        normalized_status, raw_status = _normalize_apac_status(assertion, confidence)
        dates = assertion.get("dates", {}) or {}
        effective = dates.get("effective") or dates.get("finalized")
        citation_tier = _get_apac_citation_tier(assertion)
        if not _passes_apac_quality_gate(
            confidence=confidence,
            raw_status=raw_status,
            citation_tier=citation_tier,
            strict_mode=strict_mode,
            min_confidence=min_confidence,
            require_primary_citation=require_primary_citation,
        ):
            continue

        summaries.append(
            APACAssertionSummary(
                id=assertion.get("id", ""),
                assertion=assertion.get("assertion", ""),
                country=_derive_country(assertion.get("id", "")),
                status=raw_status,
                normalized_status=normalized_status,
                confidence=round(confidence, 2),
                effective_date=effective,
                threshold_value=assertion.get("threshold_value"),
                jerk_signal=bool(assertion.get("jerk_signal", False)),
                litigation_relevance=assertion.get("litigation_relevance", "low"),
                compound_class=assertion.get("compound_class", ""),
                citation_tier=citation_tier,
            )
        )

    summaries.sort(key=lambda s: (s.country, -s.confidence, s.id))
    return summaries


def _get_fluoropolymer_exposure(material: str) -> Optional[str]:
    if material.upper() not in FLUOROPOLYMER_MATERIALS:
        return None

    trajectory = _get_apac_trajectory()
    segments: List[str] = []
    for key in ("japan", "south_korea", "china", "australia", "singapore", "taiwan", "india"):
        data = trajectory.get(key, {})
        exposure = data.get("fluoropolymer_exposure")
        if exposure:
            label = key.replace("_", " ").title()
            segments.append(f"{label}: {exposure}")

    if not segments:
        return None
    return " | ".join(segments[:3])


def _trajectory_to_stage(current_status: str, momentum: str) -> str:
    current = (current_status or "").lower()
    if "enforced" in current:
        return "enacted"
    if "final" in current:
        return "final_pending"

    m = (momentum or "").lower()
    if "high" in m:
        return "final_pending"
    if "medium" in m:
        return "proposed"
    return "under_consideration"


def _build_apac_cascade_predictions(material: str) -> Dict[str, "CascadePrediction"]:
    trajectory = _get_apac_trajectory()
    material_upper = material.upper()

    country_meta = [
        ("japan", "Japan", ["PFOS", "PFOA", "PTFE"]),
        ("south_korea", "SouthKorea", ["PFOA", "PFOS", "PFHxS"]),
        ("china", "China", ["PFOA", "PFOS", "Long-chain PFCAs", "PTFE", "PVDF"]),
        ("australia", "Australia", ["PFOS", "PFOA", "PFHxS", "PFBS"]),
        ("singapore", "Singapore", ["PFOS", "PFOA", "PFHxS", "AFFF"]),
        ("taiwan", "Taiwan", ["PFOA", "PFOS", "PFHxS", "PTFE"]),
        ("india", "India", ["PTFE", "PFAS food-contact materials"]),
    ]

    predictions: Dict[str, CascadePrediction] = {}
    for key, label, products in country_meta:
        data = trajectory.get(key)
        if not data:
            continue

        affected_products = []
        if material_upper in FLUOROPOLYMER_MATERIALS or material_upper in {"PFOA", "PFOS", "PFHXS", "GENX", "TFA"}:
            affected_products = products

        predictions[f"APAC_{label}_Trajectory"] = CascadePrediction(
            status=data.get("current_status", ""),
            regulatory_stage=_trajectory_to_stage(data.get("current_status", ""), data.get("momentum", "")),
            source=data.get("next_milestone", "APAC regulatory trajectory"),
            affected_products=affected_products,
        )

    return predictions


def _assertion_country(assertion: Dict[str, Any]) -> str:
    assertion_id = str(assertion.get("id") or "")
    prefix = assertion_id.split("_", 1)[0].upper() if assertion_id else "APAC"
    return ASSERTION_PREFIX_COUNTRY_MAP.get(prefix, prefix or "Unknown")


def _assertion_stage(assertion: Dict[str, Any]) -> str:
    raw = str(assertion.get("status") or "").lower()
    if raw in {"enforced"}:
        return "enacted"
    if raw in {"adopted"}:
        return "final_pending"
    if raw in {"consultation"}:
        return "under_consideration"
    if raw in {"proposed"}:
        return "proposed"
    if raw in {"withdrawn"}:
        return "monitoring"
    return "monitoring"


def _assertion_effective_date(assertion: Dict[str, Any]) -> Optional[str]:
    dates = assertion.get("dates", {}) or {}
    if not isinstance(dates, dict):
        return None
    return dates.get("effective") or dates.get("finalized") or dates.get("proposed")


def _assertion_source(assertion: Dict[str, Any]) -> Optional[str]:
    citations = assertion.get("citations", [])
    if not isinstance(citations, list) or not citations:
        return None
    primary = next((c for c in citations if isinstance(c, dict) and c.get("tier") == "primary"), None)
    ref = primary or next((c for c in citations if isinstance(c, dict)), None)
    if not ref:
        return None
    source = str(ref.get("source") or "").strip()
    url = str(ref.get("url") or "").strip()
    if source and url:
        return f"{source} ({url})"
    return source or url or None


def _affected_products_from_class(compound_class: str, material: str) -> List[str]:
    cls = str(compound_class or "").strip().lower()
    material_u = material.upper()
    if not cls:
        return [material_u]
    if "pfas_class" in cls or "all pfas" in cls:
        return ["All PFAS-containing products"]
    if "fluoropolymer" in cls or "pfas_and_fluoropolymer" in cls:
        return ["PTFE", "FEP", "PFA", "PVDF", "ETFE"]
    if "genx" in cls or "hfpo" in cls:
        return ["GenX", "HFPO-DA"]
    if "pfoa" in cls:
        return ["PFOA"]
    if "pfos" in cls:
        return ["PFOS"]
    if "pfhxs" in cls:
        return ["PFHxS"]
    if "pfna" in cls:
        return ["PFNA"]
    if "tfa" in cls:
        return ["TFA"]
    return [material_u]


def _assertion_matches_material_for_forecast(assertion: Dict[str, Any], material: str) -> bool:
    material_u = material.upper()
    material_l = material_u.lower()
    aliases = {material_l}
    if material_u == "GENX":
        aliases.update({"genx", "hfpo-da", "hfpo"})
    if material_u == "HFPO-DA":
        aliases.update({"genx", "hfpo-da", "hfpo"})

    compound_class = str(assertion.get("compound_class") or "").lower()
    assertion_text = str(assertion.get("assertion") or "").lower()
    assertion_id = str(assertion.get("id") or "").lower()

    if material_u in APAC_COMPOUND_MATCH:
        allowed = {str(x).lower() for x in APAC_COMPOUND_MATCH[material_u]}
        if compound_class in allowed:
            return True

    if any(alias in compound_class or alias in assertion_text or alias in assertion_id for alias in aliases):
        return True

    if material_u in FLUOROPOLYMER_MATERIALS and (
        "fluoropolymer" in compound_class or "pfas_and_fluoropolymer" in compound_class
    ):
        return True

    if material_u in PFAS_MATERIALS and "pfas_class" in compound_class:
        return True

    return False


def _build_assertion_backed_forecast(material: str, limit: int = 120) -> Dict[str, "CascadePrediction"]:
    store = _get_assertion_store()
    rows = store.list_assertions(status="approved", limit=5000)
    material_u = material.upper()

    matched: List[Dict[str, Any]] = [
        row for row in rows if _assertion_matches_material_for_forecast(row, material_u)
    ]
    if not matched and material_u in PFAS_MATERIALS:
        matched = [row for row in rows if "pfas_class" in str(row.get("compound_class") or "").lower()]

    def _sort_key(row: Dict[str, Any]) -> tuple:
        stage = _assertion_stage(row)
        parsed = _parse_date(_assertion_effective_date(row))
        # Newer dated items first within stage buckets.
        date_rank = -(parsed.toordinal() if parsed else -1)
        return (CASCADE_STAGE_ORDER.get(stage, 9), date_rank, str(row.get("id") or ""))

    matched_sorted = sorted(matched, key=_sort_key)[: max(1, int(limit))]
    predictions: Dict[str, CascadePrediction] = {}
    for row in matched_sorted:
        assertion_id = str(row.get("id") or "").strip()
        if not assertion_id:
            continue
        country = _assertion_country(row)
        predictions[assertion_id] = CascadePrediction(
            status=f"{country}: {str(row.get('assertion') or '').strip()}",
            regulatory_stage=_assertion_stage(row),
            source=_assertion_source(row),
            affected_products=_affected_products_from_class(
                str(row.get("compound_class") or ""),
                material_u,
            ),
        )
    return predictions


def get_fate_data() -> Dict[str, Any]:
    """Load and cache the real pfas_fate_v2.json literature corpus."""
    global _fate_cache
    if _fate_cache is None:
        if PFAS_FATE_V2_JSON.exists():
            try:
                with open(PFAS_FATE_V2_JSON, encoding="utf-8") as f:
                    _fate_cache = json.load(f)
                logger.info(
                    f"Loaded fate corpus: {len(_fate_cache.get('pathways', []))} pathways "
                    f"from {_fate_cache.get('metadata', {}).get('papers_processed', 0)} papers"
                )
            except Exception as e:
                logger.error(f"Failed to load fate data: {e}")
                _fate_cache = {"pathways": [], "metadata": {}}
        else:
            logger.warning(f"Fate data not found: {PFAS_FATE_V2_JSON}")
            _fate_cache = {"pathways": [], "metadata": {}}
    return _fate_cache


def get_degradation_products_from_literature(material: str) -> Dict[str, Any]:
    """
    Pull degradation products from real pfas_fate_v2.json literature data.
    Returns dict with products list and metadata about sources.
    """
    fate_data = get_fate_data()
    mat_upper = material.upper()

    # Find all pathways where this material is the precursor
    matching_pathways = [
        p for p in fate_data.get("pathways", [])
        if mat_upper in p.get("precursor", "").upper()
    ]

    if not matching_pathways:
        return {
            "products": [],
            "pathway_count": 0,
            "paper_count": 0,
            "sample_dois": [],
            "source": "No literature data available for this material",
        }

    # Extract unique products
    products = list(set(
        p.get("product", "") for p in matching_pathways if p.get("product")
    ))

    # Collect unique DOIs
    all_dois: set[str] = set()
    for pathway in matching_pathways:
        for doi in pathway.get("source_dois", []):
            if doi:
                all_dois.add(doi)

    # Get sample DOIs for display (top 3)
    sample_dois = sorted(all_dois)[:3]

    return {
        "products": sorted(products)[:15],  # Limit to 15 for UI
        "pathway_count": len(matching_pathways),
        "paper_count": len(all_dois),
        "sample_dois": sample_dois,
        "source": "BoundState Literature Corpus (peer-reviewed)",
    }


def _load_regulatory_framework() -> Dict[str, List[Dict[str, Any]]]:
    """Load regulatory framework from YAML."""
    framework: Dict[str, List[Dict[str, Any]]] = {}

    if REGULATORY_FRAMEWORK_YAML.exists():
        try:
            with open(REGULATORY_FRAMEWORK_YAML, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "regulatory_framework" in data:
                framework = data["regulatory_framework"]
                logger.info(f"Loaded regulatory data for {len(framework)} compounds from YAML")
        except Exception as e:
            logger.error(f"Failed to load regulatory framework: {e}")

    return framework


def get_regulatory_database() -> Dict[str, Dict[str, Any]]:
    """Get or build regulatory database (cached)."""
    global _regulatory_cache
    if _regulatory_cache is None:
        _regulatory_cache = _build_regulatory_database()
    return _regulatory_cache


def _build_regulatory_database() -> Dict[str, Dict[str, Any]]:
    """Build regulatory database from YAML and fallback data."""
    database: Dict[str, Dict[str, Any]] = {}

    # Load from YAML
    yaml_data = _load_regulatory_framework()

    for compound, entries in yaml_data.items():
        compound_upper = compound.upper()
        flags = []

        for entry in entries:
            flags.append(RegulatoryFlag(
                jurisdiction=entry.get("jurisdiction", "Unknown"),
                regulation=entry.get("driver", "General regulation"),
                status=_normalize_framework_status(entry.get("status", "Under review")),
                effective_date=entry.get("effective"),
                limit=None,
            ))

        # Determine if regulated based on flags
        is_regulated = any(
            "ban" in (f.status or "").lower() or
            "restrict" in (f.status or "").lower() or
            "enforceable" in (f.status or "").lower()
            for f in flags
        )

        # Determine risk level
        risk_level = "UNKNOWN"
        compound_lower = compound_upper.lower()
        if any(x in compound_lower for x in ["pfoa", "pfos"]):
            risk_level = "CRITICAL"
            is_regulated = True
        elif any(x in compound_lower for x in ["genx", "pfna", "pfda", "pfhxs"]):
            risk_level = "HIGH"
            is_regulated = True
        elif any(x in compound_lower for x in ["pfhxa", "tfa", "pfba"]):
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        database[compound_upper] = {
            "is_pfas": any(x in compound_lower for x in ["pf", "tfa", "genx"]),
            "is_regulated": is_regulated,
            "risk_level": risk_level,
            "flags": flags,
            "degradation_concerns": [],
        }

    # Merge with fallback data (fallback takes precedence for well-defined compounds)
    for name, data in FALLBACK_REGULATORY_DATA.items():
        if name not in database:
            database[name] = data
        else:
            # Merge flags if fallback has more detail
            if data.get("flags") and len(data["flags"]) > len(database[name]["flags"]):
                database[name]["flags"] = data["flags"]
            if data.get("degradation_concerns"):
                database[name]["degradation_concerns"] = data["degradation_concerns"]
            if data.get("risk_level") != "UNKNOWN":
                database[name]["risk_level"] = data["risk_level"]

    logger.info(f"Built regulatory database with {len(database)} compounds")
    return database


class RegulatoryFlag(BaseModel):
    """A regulatory flag for a compound."""
    jurisdiction: str
    regulation: str
    status: str
    effective_date: Optional[str]
    limit: Optional[str]


class RegulatoryStatus(BaseModel):
    """Regulatory status for frontend display."""
    framework: str
    status: str
    limit_ppb: Optional[float] = None
    effective_date: Optional[str] = None
    notes: str


class MaterialRegulatory(BaseModel):
    """Regulatory status for a material."""
    material: str
    is_pfas: bool
    is_regulated: bool
    risk_level: str
    flags: List[RegulatoryFlag]
    degradation_concerns: List[str]


class RegulatoryCheckResponse(BaseModel):
    """Response for regulatory check - matches frontend RegulatoryCheck interface."""
    material: str
    degradation_products: List[str]
    degradation_pathway_count: int = 0
    degradation_paper_count: int = 0
    degradation_sample_dois: List[str] = []
    degradation_source: str = ""
    frameworks_checked: int
    compliant: List[RegulatoryStatus]
    non_compliant: List[RegulatoryStatus]
    warnings: List[RegulatoryStatus]
    overall_risk: str
    apac_assertions: List[APACAssertionSummary] = []
    apac_jurisdiction_count: int = 0
    fluoropolymer_exposure: Optional[str] = None


class APACAssertionSummary(BaseModel):
    """APAC assertion summary for /check response."""

    id: str
    assertion: str
    country: str
    status: str
    normalized_status: str
    confidence: float
    effective_date: Optional[str] = None
    threshold_value: Optional[str] = None
    jerk_signal: bool = False
    litigation_relevance: str = "low"
    compound_class: str
    citation_tier: str = "secondary"


class APACAssertionDetail(BaseModel):
    """Full APAC assertion for /apac deep-dive endpoint."""

    id: str
    assertion: str
    country: str
    compound_class: str
    status: str
    normalized_status: str
    confidence: float
    effective_date: Optional[str] = None
    threshold_value: Optional[str] = None
    jerk_signal: bool = False
    litigation_relevance: str = "low"
    context: List[str] = []
    citations: List[Dict[str, Any]] = []
    exemptions: List[str] = []


class APACResponse(BaseModel):
    """Response model for APAC regulatory detail endpoint."""

    total_assertions: int
    filtered_assertions: int
    assertions: List[APACAssertionDetail]
    trajectory: Optional[Dict[str, Any]] = None


class APACQualityIssue(BaseModel):
    """Quality issue bucket for APAC assertions."""

    reason: str
    assertion_ids: List[str]


class APACQualityAuditResponse(BaseModel):
    """Quality audit summary for APAC assertions."""

    total_assertions: int
    strict_mode_defaults: Dict[str, Any]
    status_counts: Dict[str, int]
    confidence_band_counts: Dict[str, int]
    citation_tier_counts: Dict[str, int]
    strict_pass_count: int
    strict_excluded_count: int
    issues: List[APACQualityIssue]


# Fallback regulatory data for well-known compounds
FALLBACK_REGULATORY_DATA = {
    "PTFE": {
        "is_pfas": False,
        "is_regulated": False,
        "risk_level": "LOW",
        "flags": [],
        "degradation_concerns": [
            "Thermal degradation above 400°C produces TFA (trifluoroacetic acid)",
            "HF (hydrogen fluoride) released at high temperatures",
            "Processing residuals may contain PFOA traces in legacy products",
        ],
    },
    "PVDF": {
        "is_pfas": False,
        "is_regulated": False,
        "risk_level": "LOW",
        "flags": [],
        "degradation_concerns": [
            "HF release possible during thermal events",
            "Generally considered safe in normal operating conditions",
        ],
    },
    "PFOA": {
        "is_pfas": True,
        "is_regulated": True,
        "risk_level": "CRITICAL",
        "flags": [
            RegulatoryFlag(
                jurisdiction="US EPA",
                regulation="SDWA - Drinking Water MCL",
                status="Enforceable",
                effective_date="2024-04-10",
                limit="4 ppt",
            ),
            RegulatoryFlag(
                jurisdiction="EU",
                regulation="Stockholm Convention - POPs",
                status="Banned",
                effective_date="2020-07-04",
                limit="Complete ban",
            ),
            RegulatoryFlag(
                jurisdiction="California",
                regulation="Prop 65",
                status="Listed",
                effective_date="2017-11-10",
                limit="Warning required",
            ),
        ],
        "degradation_concerns": [
            "Persistent in environment - no natural degradation pathway",
            "Bioaccumulates in humans and wildlife",
            "Linked to cancer, thyroid disease, immune effects",
        ],
    },
    "PFOS": {
        "is_pfas": True,
        "is_regulated": True,
        "risk_level": "CRITICAL",
        "flags": [
            RegulatoryFlag(
                jurisdiction="US EPA",
                regulation="SDWA - Drinking Water MCL",
                status="Enforceable",
                effective_date="2024-04-10",
                limit="4 ppt",
            ),
            RegulatoryFlag(
                jurisdiction="EU",
                regulation="Stockholm Convention - POPs",
                status="Banned",
                effective_date="2009-05-01",
                limit="Complete ban",
            ),
        ],
        "degradation_concerns": [
            "Extremely persistent - classified as 'forever chemical'",
            "Found in AFFF firefighting foam",
            "Major litigation target",
        ],
    },
    "GenX": {
        "is_pfas": True,
        "is_regulated": True,
        "risk_level": "HIGH",
        "flags": [
            RegulatoryFlag(
                jurisdiction="US EPA",
                regulation="Health Advisory",
                status="Advisory",
                effective_date="2022-06-15",
                limit="10 ppt",
            ),
            RegulatoryFlag(
                jurisdiction="North Carolina",
                regulation="DEQ Health Goal",
                status="Enforceable",
                effective_date="2019-01-01",
                limit="140 ppt",
            ),
        ],
        "degradation_concerns": [
            "PFOA replacement - similar persistence concerns",
            "Active litigation in North Carolina",
            "Potential for broader regulation",
        ],
    },
}

UPCOMING_REGULATIONS = [
    {
        "jurisdiction": "EU",
        "regulation": "Universal PFAS Restriction",
        "status": "Proposed",
        "expected_date": "2025-2026",
        "description": "Comprehensive ban on all PFAS substances",
    },
    {
        "jurisdiction": "US EPA",
        "regulation": "CERCLA Hazardous Substance",
        "status": "Final Rule Expected",
        "expected_date": "2024",
        "description": "PFOA/PFOS designated as hazardous substances",
    },
]


class CascadeItem(BaseModel):
    """A single regulatory cascade event."""
    year: int
    jurisdiction: str
    regulation: str
    impact: str
    probability: float


class CascadePrediction(BaseModel):
    """A cascade prediction for frontend display."""
    status: str
    regulatory_stage: str  # "enacted", "final_pending", "proposed", "under_consideration", "monitoring"
    source: Optional[str] = None  # Citation like "ECHA Proposal 2023-02" or "EPA Final Rule 89 FR 22888"
    affected_products: List[str]


class CascadeResponse(BaseModel):
    """Regulatory cascade forecast response - matches frontend CascadeResponse interface."""
    material: str
    forecast_year: int
    predictions: Dict[str, CascadePrediction]
    recommendation: str


@router.get("/cascade", response_model=CascadeResponse)
async def get_regulatory_cascade(
    material: str = Query(..., description="Material to forecast"),
    forecast_year: int = Query(2025, description="Target year for forecast"),
) -> CascadeResponse:
    """Get regulatory cascade forecast for a material."""
    mat_upper = material.upper()
    # AssertionStore-backed forecast across APAC + Western + TFA governed corpora.
    predictions: Dict[str, CascadePrediction] = _build_assertion_backed_forecast(mat_upper)
    # Keep trajectory-only APAC entries as additive context if not already covered.
    for key, value in _build_apac_cascade_predictions(mat_upper).items():
        predictions.setdefault(key, value)

    # Generate recommendation based on material type
    database = get_regulatory_database()
    data = database.get(mat_upper, {})
    risk_level = data.get("risk_level", "UNKNOWN")

    enacted_count = sum(1 for p in predictions.values() if p.regulatory_stage == "enacted")
    proposed_count = sum(1 for p in predictions.values() if p.regulatory_stage in {"proposed", "under_consideration", "final_pending"})

    if risk_level == "CRITICAL" or enacted_count >= 5:
        recommendation = f"URGENT: {mat_upper} is subject to existing bans. Immediate phase-out required. Consult legal counsel for compliance strategy."
    elif risk_level == "HIGH" or enacted_count >= 2:
        recommendation = f"HIGH PRIORITY: {mat_upper} faces significant regulatory pressure. Begin evaluating alternatives and supply chain impacts."
    elif proposed_count > 0 or mat_upper in ["PTFE", "PVDF", "FEP", "PFA", "ETFE"]:
        recommendation = f"MONITOR: {mat_upper} may face restrictions by {forecast_year + 1}. Track EU REACH proposal and prepare for potential use restrictions."
    else:
        recommendation = f"LOW RISK: {mat_upper} not currently targeted but monitor regulatory developments as PFAS definition expands."

    return CascadeResponse(
        material=mat_upper,
        forecast_year=forecast_year,
        predictions=predictions,
        recommendation=recommendation,
    )


@router.get("/check", response_model=RegulatoryCheckResponse)
async def check_regulatory(
    material: str = Query(..., description="Material to check"),
    include_degradation: bool = Query(True, description="Include degradation concerns"),
) -> RegulatoryCheckResponse:
    """Check regulatory status for a material - returns format matching frontend RegulatoryCheck interface."""
    mat_upper = material.upper()
    database = get_regulatory_database()

    data = database.get(mat_upper, {
        "is_pfas": False,
        "is_regulated": False,
        "risk_level": "UNKNOWN",
        "flags": [],
        "degradation_concerns": ["No specific data available for this material"],
    })

    flags = data.get("flags", [])

    apac_assertions = _get_apac_assertion_summaries(mat_upper)
    apac_jurisdiction_count = len({a.country for a in apac_assertions if a.country != "APAC"})
    fluoropolymer_exposure = _get_fluoropolymer_exposure(mat_upper)

    # Build compliant/non_compliant/warnings lists
    compliant: List[RegulatoryStatus] = []
    non_compliant: List[RegulatoryStatus] = []
    warnings: List[RegulatoryStatus] = []

    # Define frameworks to check
    frameworks = [
        ("US EPA SDWA", "drinking water"),
        ("EU REACH", "chemicals regulation"),
        ("Stockholm Convention", "persistent organic pollutants"),
        ("CA Prop 65", "carcinogens and reproductive toxicants"),
        ("US TSCA", "toxic substances control"),
        ("Japan CSCL", "chemical substances control"),
        ("South Korea K-REACH", "chemical registration"),
        ("China MEE", "new pollutants management"),
        ("Australia NHMRC", "drinking water guidelines"),
        ("Singapore NEA", "hazardous substances"),
        ("Taiwan MOENV", "toxic chemical substances"),
        ("India FSSAI", "food contact materials"),
    ]

    for flag in flags:
        # Parse limit to ppb if available
        limit_ppb = None
        if flag.limit:
            try:
                # Extract numeric value from limit string like "4 ppt"
                limit_str = flag.limit.split()[0]
                limit_val = float(limit_str)
                if "ppt" in flag.limit.lower():
                    limit_ppb = limit_val / 1000
                elif "ppb" in flag.limit.lower():
                    limit_ppb = limit_val
            except (ValueError, IndexError):
                pass

        status_item = RegulatoryStatus(
            framework=f"{flag.jurisdiction} - {flag.regulation}",
            status=flag.status.lower(),
            limit_ppb=limit_ppb,
            effective_date=flag.effective_date,
            notes=f"Limit: {flag.limit}" if flag.limit else f"Status: {flag.status}",
        )

        # Categorize by status
        status_lower = flag.status.lower()
        if status_lower in ["banned", "enforceable", "restricted"]:
            non_compliant.append(status_item)
        elif status_lower in ["advisory", "listed", "monitored"]:
            warnings.append(status_item)
        else:
            compliant.append(status_item)

    # Add compliant frameworks (those not in flags)
    checked_frameworks = {f"{fl.jurisdiction} - {fl.regulation}" for fl in flags}
    for framework_name, framework_desc in frameworks:
        full_name = framework_name
        if full_name not in checked_frameworks:
            # Only add as compliant for materials that aren't regulated
            if not data["is_regulated"]:
                compliant.append(RegulatoryStatus(
                    framework=framework_name,
                    status="compliant",
                    limit_ppb=None,
                    effective_date=None,
                    notes=f"No restrictions under {framework_desc}",
                ))

    # Get degradation products from real literature corpus
    degradation_data: Dict[str, Any] = {"products": [], "pathway_count": 0, "paper_count": 0, "sample_dois": [], "source": ""}
    degradation_products: List[str] = []

    if include_degradation:
        # Pull from real pfas_fate_v2.json literature data
        degradation_data = get_degradation_products_from_literature(mat_upper)
        degradation_products = degradation_data["products"]

        # Fallback for materials not in literature corpus
        if not degradation_products:
            fallback_map = {
                "PTFE": ["TFA", "HF", "CF4", "COF2"],
                "PVDF": ["HF", "VDF"],
                "FEP": ["TFA", "HF", "CF4"],
                "PFA": ["TFA", "HF"],
                "ETFE": ["TFA", "HF", "HCl"],
                "ECTFE": ["TFA", "HF", "HCl"],
                "PFOA": ["Persistent - no degradation"],
                "PFOS": ["Persistent - no degradation"],
                "GENX": ["HFPO-DA"],
            }
            degradation_products = fallback_map.get(mat_upper, [])
            degradation_data["source"] = "Fallback data (limited literature coverage)"

    # Determine overall risk
    if non_compliant:
        if data.get("risk_level") == "CRITICAL":
            overall_risk = "HIGH"
        else:
            overall_risk = "MEDIUM"
    elif warnings:
        overall_risk = "LOW"
    else:
        overall_risk = "COMPLIANT"

    return RegulatoryCheckResponse(
        material=mat_upper,
        degradation_products=degradation_products,
        degradation_pathway_count=degradation_data.get("pathway_count", 0),
        degradation_paper_count=degradation_data.get("paper_count", 0),
        degradation_sample_dois=degradation_data.get("sample_dois", []),
        degradation_source=degradation_data.get("source", ""),
        frameworks_checked=len(frameworks),
        compliant=compliant,
        non_compliant=non_compliant,
        warnings=warnings,
        overall_risk=overall_risk,
        apac_assertions=apac_assertions,
        apac_jurisdiction_count=apac_jurisdiction_count,
        fluoropolymer_exposure=fluoropolymer_exposure,
    )


@router.get("/apac", response_model=APACResponse)
async def get_apac_regulatory(
    material: Optional[str] = Query(None, description="Filter by material"),
    country: Optional[str] = Query(None, description="Filter by country code (JPN, KOR, CHN, AUS, SGP, TWN, IND, APAC)"),
    min_confidence: float = Query(
        REGULATORY_APAC_MIN_CONFIDENCE,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold.",
    ),
    strict_mode: bool = Query(
        REGULATORY_STRICT_MODE,
        description="Apply production quality gate (reject unverified assertions).",
    ),
    require_primary_citation: bool = Query(
        REGULATORY_APAC_REQUIRE_PRIMARY_CITATION,
        description="Only include assertions with at least one primary citation.",
    ),
) -> APACResponse:
    """Get APAC regulatory assertions with optional filtering."""
    all_assertions = _load_apac_assertions()

    filtered: List[APACAssertionDetail] = []
    for assertion in all_assertions:
        assertion_id = assertion.get("id", "")
        prefix = assertion_id.split("_", 1)[0].upper() if assertion_id else "APAC"

        if country and prefix != country.upper():
            continue

        if material and not _assertion_matches_material(assertion, material):
            continue

        confidence = _adjust_apac_confidence(assertion)
        if confidence < min_confidence:
            continue

        normalized_status, raw_status = _normalize_apac_status(assertion, confidence)
        citation_tier = _get_apac_citation_tier(assertion)
        if not _passes_apac_quality_gate(
            confidence=confidence,
            raw_status=raw_status,
            citation_tier=citation_tier,
            strict_mode=strict_mode,
            min_confidence=min_confidence,
            require_primary_citation=require_primary_citation,
        ):
            continue
        dates = assertion.get("dates", {}) or {}
        effective = dates.get("effective") or dates.get("finalized")

        filtered.append(
            APACAssertionDetail(
                id=assertion_id,
                assertion=assertion.get("assertion", ""),
                country=APAC_COUNTRY_MAP.get(prefix, "APAC"),
                compound_class=assertion.get("compound_class", ""),
                status=raw_status,
                normalized_status=normalized_status,
                confidence=round(confidence, 2),
                effective_date=effective,
                threshold_value=assertion.get("threshold_value"),
                jerk_signal=bool(assertion.get("jerk_signal", False)),
                litigation_relevance=assertion.get("litigation_relevance", "low"),
                context=assertion.get("context", []) or [],
                citations=assertion.get("citations", []) or [],
                exemptions=assertion.get("exemptions", []) or [],
            )
        )

    filtered.sort(key=lambda a: (a.country, -a.confidence, a.id))

    return APACResponse(
        total_assertions=len(all_assertions),
        filtered_assertions=len(filtered),
        assertions=filtered,
        trajectory=_get_apac_trajectory() if not material and not country else None,
    )


@router.get("/apac/quality-audit", response_model=APACQualityAuditResponse)
async def get_apac_quality_audit() -> APACQualityAuditResponse:
    """
    Return quality diagnostics for APAC assertions.

    This endpoint is used to enforce production rigor by exposing
    weak evidence buckets (low confidence, unverified, secondary-only).
    """
    assertions = _load_apac_assertions()

    status_counts: Counter[str] = Counter()
    confidence_band_counts: Counter[str] = Counter()
    citation_tier_counts: Counter[str] = Counter()
    low_confidence_ids: List[str] = []
    unverified_ids: List[str] = []
    secondary_only_ids: List[str] = []
    strict_pass_count = 0

    for assertion in assertions:
        assertion_id = assertion.get("id", "")
        confidence = _adjust_apac_confidence(assertion)
        _, raw_status = _normalize_apac_status(assertion, confidence)
        citation_tier = _get_apac_citation_tier(assertion)

        status_counts[raw_status] += 1
        citation_tier_counts[citation_tier] += 1

        if confidence >= 0.95:
            confidence_band_counts[">=0.95"] += 1
        elif confidence >= 0.85:
            confidence_band_counts["0.85-0.94"] += 1
        elif confidence >= 0.75:
            confidence_band_counts["0.75-0.84"] += 1
        elif confidence >= 0.60:
            confidence_band_counts["0.60-0.74"] += 1
        else:
            confidence_band_counts["<0.60"] += 1

        if confidence < REGULATORY_APAC_MIN_CONFIDENCE:
            low_confidence_ids.append(assertion_id)
        if raw_status == "unverified":
            unverified_ids.append(assertion_id)
        if citation_tier != "primary":
            secondary_only_ids.append(assertion_id)

        if _passes_apac_quality_gate(
            confidence=confidence,
            raw_status=raw_status,
            citation_tier=citation_tier,
            strict_mode=REGULATORY_STRICT_MODE,
            min_confidence=REGULATORY_APAC_MIN_CONFIDENCE,
            require_primary_citation=REGULATORY_APAC_REQUIRE_PRIMARY_CITATION,
        ):
            strict_pass_count += 1

    issues: List[APACQualityIssue] = []
    if low_confidence_ids:
        issues.append(APACQualityIssue(reason="low_confidence", assertion_ids=low_confidence_ids))
    if unverified_ids:
        issues.append(APACQualityIssue(reason="unverified_status", assertion_ids=unverified_ids))
    if secondary_only_ids:
        issues.append(APACQualityIssue(reason="secondary_only_citations", assertion_ids=secondary_only_ids))

    strict_excluded_count = len(assertions) - strict_pass_count
    return APACQualityAuditResponse(
        total_assertions=len(assertions),
        strict_mode_defaults={
            "strict_mode": REGULATORY_STRICT_MODE,
            "min_confidence": REGULATORY_APAC_MIN_CONFIDENCE,
            "require_primary_citation": REGULATORY_APAC_REQUIRE_PRIMARY_CITATION,
        },
        status_counts=dict(status_counts),
        confidence_band_counts=dict(confidence_band_counts),
        citation_tier_counts=dict(citation_tier_counts),
        strict_pass_count=strict_pass_count,
        strict_excluded_count=strict_excluded_count,
        issues=issues,
    )
