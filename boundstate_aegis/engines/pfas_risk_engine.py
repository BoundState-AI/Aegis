#!/usr/bin/env python3
"""
Module: pfas_risk_engine
Purpose: Main orchestrator for PFAS pathway risk assessment.
    PFASRiskEngine evaluates compounds against degradation pathways,
    computes risk classifications, and aggregates regulatory context
    for comprehensive PFAS exposure reporting.

    Rev History:
        1.0.0 - Initial risk engine with pathway evaluation

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from boundstate_aegis.knowledge.graph_builder import PFASKnowledgeGraph

from boundstate_aegis.config import HIGH_TEMP_THRESHOLD_C
from boundstate_aegis.models.risk_models import RiskFinding, RiskAssessmentResult

try:
    from boundstate_core.exceptions import SafetyCriticalError
except ImportError:
    # Fallback if boundstate_core not installed
    class SafetyCriticalError(Exception):
        """Safety-critical error fallback."""
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.context = context or {}

logger = logging.getLogger(__name__)


def _coerce_float(value: Any) -> Optional[float]:
    """Coerce various input types to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        trimmed = value.strip().replace("°", "").replace("C", "").replace("c", "")
        try:
            return float(trimmed)
        except ValueError:
            return None
    return None


class PFASRiskEngine:
    """
    Screening tool for identifying potential degradation pathways from precursor
    materials to regulated PFAS endpoints.

    Intended for:
        - Preliminary material screening and hypothesis generation
        - Prioritising compounds for analytical testing
        - Informing Chemours/customer diligence conversations

    Critical limitations:
        1. Screening-level only — does not estimate formation yields or rates.
        2. Literature-derived — pathways reflect available publications and may be incomplete.
        3. Simplified kinetics — temperature/atmosphere heuristics; ignores detailed kinetics.
        4. Qualitative confidence — 0-1 scale is relative, not statistical certainty.
        5. Not a compliance determination — analytical confirmation (EPA 537.1/533/8327) required.

    Regulatory context: users should interpret results alongside current EPA PFAS
    Strategic Roadmap guidance, TSCA §8 PFAS reporting requirements, and REACH
    Annex XV proposals. Absence of a flagged pathway is not proof of PFAS absence.
    """

    def __init__(self, graph: "PFASKnowledgeGraph") -> None:
        self.graph = graph

    def evaluate(
        self,
        source: str,
        context: Optional[Dict[str, Any]] = None,
        targets: Optional[Iterable[str]] = None,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        Screen potential PFAS formation pathways for a source compound under
        specified operating or incident conditions.

        Args:
            source: Name of the precursor compound to evaluate.
            context: Optional mapping describing conditions. Supported keys:
                - service_temp_c: steady-state temperature (°C)
                - incident_temp_c: maximum credible incident temperature (°C)
                - atmosphere: qualitative descriptor, e.g. "air", "oxygen-rich"
            targets: Optional iterable of PFAS targets to constrain traversal.
            max_depth: Maximum number of transformation steps to explore (default 3).

        Returns:
            Dict with keys:
                - compound_evaluated
                - scenario_context
                - pfas_findings (list)
                - summary (text)
        """
        if not source or not isinstance(source, str):
            raise ValueError("source must be a non-empty string")

        self.graph.validate_graph()

        context = context or {}

        # Import here to avoid circular imports
        from boundstate_aegis.knowledge.graph_queries import trace_pathways

        paths = trace_pathways(
            graph=self.graph,
            start_compound=source,
            targets=targets,
            max_depth=max_depth,
        )
        matching_paths = [
            path
            for path in paths
            if self._conditions_match(path.get("conditions", []), context)
        ]

        pfas_risks = [self._build_risk_entry(path) for path in matching_paths]

        findings = [
            {
                "product": entry["product"],
                "screening_classification": self._label_exposure_class(entry),
                "conditions_where_it_forms": entry["path_conditions"],
                "confidence": entry["overall_confidence"],
                "regulatory_flags": entry["regulatory_flags"],
                "evidence_refs": entry["evidence_refs"],
            }
            for entry in pfas_risks
        ]

        return {
            "compound_evaluated": source,
            "scenario_context": context,
            "pfas_findings": findings,
            "summary": self._summarize_findings(pfas_risks, context),
        }

    def assess(
        self,
        compound: str,
        scenario: Optional[Dict[str, Any]] = None,
        max_depth: int = 3,
    ) -> RiskAssessmentResult:
        """
        Higher-level assessment returning structured RiskAssessmentResult.

        Args:
            compound: Name of the precursor compound to evaluate.
            scenario: Optional conditions dict (service_temp_c, incident_temp_c, atmosphere).
            max_depth: Maximum transformation steps to explore.

        Returns:
            RiskAssessmentResult with findings and summary.
        """
        raw = self.evaluate(source=compound, context=scenario, max_depth=max_depth)

        findings = [
            RiskFinding(
                product=f["product"],
                classification=f["screening_classification"],
                confidence=f["confidence"],
                conditions=f["conditions_where_it_forms"],
                regulatory_flags=f["regulatory_flags"],
                evidence_refs=f["evidence_refs"],
            )
            for f in raw.get("pfas_findings", [])
        ]

        return RiskAssessmentResult(
            compound_evaluated=raw["compound_evaluated"],
            scenario_context=raw.get("scenario_context", {}),
            findings=findings,
            summary=raw.get("summary", ""),
        )

    def _conditions_match(
        self, path_conditions: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> bool:
        if not path_conditions:
            return True

        t = context.get("service_temp_c")
        if t is None:
            t = context.get("incident_temp_c")
        t_val = _coerce_float(t)

        ctx_atm = context.get("atmosphere")

        for cond in path_conditions:
            min_t = _coerce_float(cond.get("min_temp_c"))
            max_t = _coerce_float(cond.get("max_temp_c"))
            atm = cond.get("atmosphere")

            if min_t is not None and t_val is not None and t_val < min_t:
                continue
            if max_t is not None and t_val is not None and t_val > max_t:
                continue
            if atm and ctx_atm and atm != ctx_atm:
                continue

            return True

        return False

    @staticmethod
    def _listify(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(v) for v in value if v]
        return [str(value)]

    def _build_risk_entry(self, path: Dict[str, Any]) -> Dict[str, Any]:
        compound_path = path.get("path") or []
        product = compound_path[-1] if compound_path else ""
        node_attrs = (
            self.graph.get_node_attributes(product)
            if product
            else {}
        )

        path_conditions = path.get("conditions") or []
        overall_confidence = _coerce_float(path.get("confidence")) or 0.0
        regulatory_flags = self._listify(
            node_attrs.get("regulated_in") or node_attrs.get("regulatory_flags")
        )
        evidence_refs = path.get("evidence_refs") or []

        risk_entry = {
            "product": product,
            "path_conditions": path_conditions,
            "overall_confidence": overall_confidence,
            "regulatory_flags": regulatory_flags,
            "evidence_refs": evidence_refs,
            "is_short_chain_pfas": bool(node_attrs.get("is_short_chain_pfas")),
            "litigation_flag": bool(node_attrs.get("litigation_flag")),
            "disposal_only": self._is_disposal_only(path_conditions),
        }
        return risk_entry

    @staticmethod
    def _is_disposal_only(conditions: List[Dict[str, Any]]) -> bool:
        """
        True when every step requires high-temperature (≥800 °C) or explicit
        incineration/fire mechanisms, indicating an end-of-life scenario.
        """
        if not conditions:
            return False
        for cond in conditions:
            mechanism = (cond.get("mechanism") or "").lower()
            min_temp = _coerce_float(cond.get("min_temp_c"))
            high_temp = min_temp is not None and min_temp >= HIGH_TEMP_THRESHOLD_C
            incineration = "incineration" in mechanism or "fire" in mechanism
            if not (high_temp or incineration):
                return False
        return True

    def _label_exposure_class(self, risk_entry: Dict[str, Any]) -> str:
        regulatory_flags = risk_entry.get("regulatory_flags") or []
        if regulatory_flags or risk_entry.get("litigation_flag"):
            return (
                "Potential formation of PFAS compounds already subject to regulatory "
                "action or litigation"
            )
        if risk_entry.get("is_short_chain_pfas"):
            return (
                "Short-chain PFAS (C4–C7) with high mobility and elevated regulatory "
                "priority"
            )
        if risk_entry.get("disposal_only"):
            return (
                f"Pathway requires ≥{HIGH_TEMP_THRESHOLD_C:.0f} °C oxidative conditions typical of fire or "
                "incineration scenarios"
            )
        if risk_entry.get("overall_confidence", 1.0) < 0.4:
            return (
                "Preliminary indication only; limited literature support "
                "(analytical confirmation required)"
            )
        return (
            "Pathway identified under provided conditions. Screening-level only; "
            "analytical confirmation required"
        )

    def _summarize_findings(
        self, pfas_risks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> str:
        if not pfas_risks:
            return (
                "No degradation pathways to regulated PFAS or short-chain PFAS were "
                "identified under the specified conditions based on available "
                "literature. This does not guarantee PFAS will not form. Analytical "
                "confirmation (EPA 537.1 / 533 / 8327 or equivalent) remains "
                "recommended for high-consequence use cases."
            )

        service_temp = _coerce_float(context.get("service_temp_c"))
        incident_temp = _coerce_float(context.get("incident_temp_c"))
        atmosphere = context.get("atmosphere")

        def _format_context_phrase() -> str:
            parts: List[str] = []
            if service_temp is not None:
                parts.append(f"service temperatures near {service_temp:.0f} °C")
            if incident_temp is not None:
                parts.append(f"incident temperatures near {incident_temp:.0f} °C")
            if atmosphere:
                parts.append(f"{atmosphere} atmosphere")
            if not parts:
                return "the indicated operating envelope"
            if len(parts) == 1:
                return parts[0]
            return ", ".join(parts[:-1]) + f", and {parts[-1]}"

        high_scrutiny = [
            r for r in pfas_risks if r.get("regulatory_flags") or r.get("litigation_flag")
        ]
        if high_scrutiny:
            return (
                "One or more literature-reported transformation pathways indicate "
                "potential formation of PFAS compounds already under active "
                "regulatory or litigation scrutiny. These pathways align with the "
                f"higher-temperature or oxidative conditions associated with "
                f"{_format_context_phrase()}. Analytical confirmation using "
                "EPA-validated methods is strongly recommended."
            )

        disposal_only = [r for r in pfas_risks if r.get("disposal_only")]
        if disposal_only and len(disposal_only) == len(pfas_risks):
            return (
                f"All identified PFAS pathways require high-temperature oxidative "
                f"conditions (≥{HIGH_TEMP_THRESHOLD_C:.0f} °C), such as incineration or fire scenarios, rather "
                f"than the described normal operating envelope ({_format_context_phrase()}). "
                "Formation under normal service conditions is not anticipated based "
                "on available literature, but disposal and incident response plans "
                "should assume potential PFAS formation and verify analytically."
            )

        low_confidence = [
            r for r in pfas_risks if r.get("overall_confidence", 0.0) < 0.4
        ]
        if low_confidence and len(low_confidence) == len(pfas_risks):
            return (
                "Potential PFAS pathways were identified, but all currently carry low "
                "qualitative confidence due to limited literature support. Treat these "
                "as preliminary only. Supplier process and aging data plus analytical "
                "confirmation are required before drawing conclusions."
            )

        return (
            "Potential PFAS pathways were identified under the specified conditions. "
            "Follow-up analytical testing (EPA 537.1 / 533 / 8327 or equivalent) and "
            "supplier operational or aging data are recommended to refine likelihood "
            "and regulatory exposure. This is a screening-level result, not a "
            "compliance determination."
        )

    @staticmethod
    def context_normal_service() -> Dict[str, Any]:
        """Default context for steady-state hyperscaler or industrial service loops."""
        return {
            "service_temp_c": 60.0,
            "atmosphere": "air",
        }

    @staticmethod
    def context_fire_event() -> Dict[str, Any]:
        """Context for acute fire or thermal runaway scenarios."""
        return {
            "incident_temp_c": 800.0,
            "atmosphere": "air",
        }

    @staticmethod
    def context_incineration() -> Dict[str, Any]:
        """Context for end-of-life high-temperature oxidative destruction."""
        return {
            "incident_temp_c": 1000.0,
            "atmosphere": "oxygen-rich",
        }

    @staticmethod
    def get_regulatory_disclaimer() -> str:
        """
        Full legal/regulatory disclaimer for any external PFAS reporting.
        Do not shorten or alter when presenting to customers or counsel.
        """
        return """
REGULATORY DISCLAIMER

This screening analysis is based on literature-reported degradation pathways
and thermodynamic thresholds. It does NOT constitute a comprehensive PFAS risk
assessment, compliance determination, or safety evaluation.

ANALYSIS SCOPE AND LIMITATIONS:
1. SCREENING-LEVEL PREDICTIONS ONLY – identifies theoretical pathways only.
2. LITERATURE-DERIVED MECHANISMS – may be incomplete for novel compounds.
3. SIMPLIFIED KINETIC MODELING – ignores Arrhenius kinetics, residence time, etc.
4. QUALITATIVE CONFIDENCE SCORES – not statistical confidence intervals.

REQUIRED FOLLOW-UP:
– Analytical confirmation via EPA Methods 537.1, 533, 8327 or equivalent.
– Process-specific validation with material suppliers.
– Regulatory consultation referencing EPA PFAS Strategic Roadmap (2024),
  40 CFR Part 747 (TSCA §8 PFAS reporting), CWA/SDWA PFAS limits,
  and REACH Annex XV restrictions.

ABSENCE OF EVIDENCE IS NOT EVIDENCE OF ABSENCE.

This disclaimer applies to all outputs generated by the PFAS Risk Engine.
Version date: October 2025.
        """.strip()
