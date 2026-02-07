#!/usr/bin/env python3
"""
Module: publication_dynamics
Purpose: Publication dynamics analysis for litigation risk modeling.
    Tracks scientific attention using physics-inspired temporal derivatives:
    - Position: Total papers mentioning a compound
    - Velocity: Rate of new publications (papers/year)
    - Acceleration: Change in velocity (is research accelerating?)
    - Jerk: Change in acceleration (inflection points)

    Rev History:
        1.0.0 - Initial publication dynamics analysis
        1.0.1 - Terminology cleanup

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
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Year extraction patterns from PDF filenames
YEAR_PATTERNS = [
    # Elsevier pattern: S0045653521002460 -> extract 21 -> 2021
    (r"S\d{6}(\d{2})\d{6}", lambda m: 2000 + int(m.group(1))),
    # Explicit year in filename: _2025_ or -2025-
    (r"[_-](20[0-2]\d)[_-]", lambda m: int(m.group(1))),
    # Year at end: paper_2024.pdf
    (r"[_-](20[0-2]\d)\.pdf$", lambda m: int(m.group(1))),
    # Year in parentheses or brackets
    (r"[\(\[](20[0-2]\d)[\)\]]", lambda m: int(m.group(1))),
]

# Content signal keywords for qualitative risk
HEALTH_KEYWORDS = {
    "toxicity", "toxic", "immunotoxicity", "carcinogenic", "cancer",
    "developmental", "reproductive", "thyroid", "liver", "kidney",
    "health effects", "adverse effects", "mortality", "morbidity"
}

CONTAMINATION_KEYWORDS = {
    "groundwater", "drinking water", "contamination", "contaminated",
    "bioaccumulation", "food chain", "exposure", "serum levels",
    "blood levels", "environmental persistence", "soil contamination"
}

REGULATORY_KEYWORDS = {
    "epa", "cercla", "mcl", "banned", "restriction", "phase-out",
    "regulation", "regulatory", "limit", "standard", "guideline",
    "stockholm convention", "reach", "prohibition"
}

# Compound name normalization
COMPOUND_ALIASES = {
    "PFOA": ["PFOA", "perfluorooctanoic acid", "C8"],
    "PFOS": ["PFOS", "perfluorooctane sulfonic", "perfluorooctanesulfonate"],
    "PTFE": ["PTFE", "teflon", "polytetrafluoroethylene"],
    "PVDF": ["PVDF", "polyvinylidene fluoride", "polyvinylidene difluoride"],
    "FEP": ["FEP", "fluorinated ethylene propylene"],
    "PFA": ["PFA", "perfluoroalkoxy"],
    "ETFE": ["ETFE", "ethylene tetrafluoroethylene"],
    "TFA": ["TFA", "trifluoroacetic acid"],
    "GENX": ["GenX", "HFPO-DA", "hexafluoropropylene oxide dimer acid"],
    "PFNA": ["PFNA", "perfluorononanoic acid"],
    "PFDA": ["PFDA", "perfluorodecanoic acid"],
    "PFHXS": ["PFHxS", "perfluorohexane sulfonic"],
    "HF": ["HF", "hydrogen fluoride", "hydrofluoric acid"],
}


def extract_year_from_filename(filename: str) -> Optional[int]:
    """Extract publication year from PDF filename."""
    for pattern, extractor in YEAR_PATTERNS:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            year = extractor(match)
            if 1990 <= year <= 2030:  # Sanity check
                return year
    return None


def extract_year_from_reference(ref: str) -> Optional[int]:
    """Extract year from a reference string."""
    if not ref:
        return None
    return extract_year_from_filename(ref)


class PublicationDynamics:
    """
    Calculate publication dynamics (position/velocity/acceleration/jerk).

    Uses literature data to compute temporal derivatives that indicate
    emerging litigation risk based on research attention trends.
    """

    def __init__(self, evidence_path: Optional[Path] = None, pdf_dir: Optional[Path] = None):
        """
        Initialize with evidence data.

        Args:
            evidence_path: Path to pfas_lit_summary.json
            pdf_dir: Optional path to PDF directory for additional year extraction
        """
        self.evidence_path = evidence_path
        self.pdf_dir = pdf_dir

        # Loaded data
        self.entries: List[Dict[str, Any]] = []
        self.references: Set[str] = set()

        # Computed timeseries: compound -> {year: count}
        self.compound_years: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.global_years: Dict[int, int] = defaultdict(int)

        # Content signals: compound -> {keyword_type: count}
        self.content_signals: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        if evidence_path and evidence_path.exists():
            self._load_evidence(evidence_path)

        if pdf_dir and pdf_dir.exists():
            self._load_pdf_years(pdf_dir)

    def _load_evidence(self, path: Path) -> None:
        """Load and process evidence from JSON file."""
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load evidence from {path}: {e}")
            return

        # Handle both legacy flat list and new {metadata, evidence} schema
        if isinstance(raw, dict):
            self.entries = raw.get("evidence", [])
        elif isinstance(raw, list):
            self.entries = raw
        else:
            logger.error(f"Unexpected evidence format: {type(raw)}")
            return

        for entry in self.entries:
            if not isinstance(entry, dict):
                continue

            # Support both legacy (polymer/references/snippet) and new (precursor/doi/verbatim_snippet) schemas
            polymer = (entry.get("polymer") or entry.get("precursor") or "").upper()
            refs = entry.get("references", [])
            if not refs:
                doi = entry.get("doi", "")
                refs = [doi] if doi else []
            snippet = (entry.get("snippet") or entry.get("verbatim_snippet") or "").lower()

            # Extract years from references
            if isinstance(refs, str):
                refs = [refs]

            for ref in refs:
                self.references.add(ref)
                year = extract_year_from_reference(ref)
                if year:
                    self.compound_years[polymer][year] += 1
                    self.global_years[year] += 1

            # Extract content signals from snippets
            self._analyze_content(polymer, snippet)

            # Also track degradation products mentioned
            pathway = entry.get("pathway", "")
            if not pathway:
                product = entry.get("product", "")
                if product:
                    pathway = f"{polymer} → {product}"
            for compound, aliases in COMPOUND_ALIASES.items():
                for alias in aliases:
                    if alias.lower() in pathway.lower() or alias.lower() in snippet:
                        # This compound is mentioned
                        for ref in refs:
                            year = extract_year_from_reference(ref)
                            if year:
                                self.compound_years[compound][year] += 1

        logger.info(f"Loaded {len(self.entries)} entries, {len(self.references)} unique references")

    def _load_pdf_years(self, pdf_dir: Path) -> None:
        """Load additional year data from PDF filenames."""
        for pdf in pdf_dir.glob("*.pdf"):
            year = extract_year_from_filename(pdf.name)
            if year:
                self.global_years[year] += 1

    def _analyze_content(self, compound: str, text: str) -> None:
        """Analyze text for content signals."""
        text_lower = text.lower()

        for keyword in HEALTH_KEYWORDS:
            if keyword in text_lower:
                self.content_signals[compound]["health"] += 1
                break

        for keyword in CONTAMINATION_KEYWORDS:
            if keyword in text_lower:
                self.content_signals[compound]["contamination"] += 1
                break

        for keyword in REGULATORY_KEYWORDS:
            if keyword in text_lower:
                self.content_signals[compound]["regulatory"] += 1
                break

    def get_position(self, compound: str) -> int:
        """
        Get position (total papers) for a compound.

        Position represents the accumulated research attention.
        Higher position = more established in literature.
        """
        compound = compound.upper()
        years = self.compound_years.get(compound, {})
        return sum(years.values())

    def get_velocity(self, compound: str, window_years: int = 3) -> float:
        """
        Get velocity (papers per year) for recent window.

        Velocity represents current research activity rate.
        Higher velocity = active research interest.
        """
        compound = compound.upper()
        years = self.compound_years.get(compound, {})

        if not years:
            return 0.0

        current_year = datetime.now().year
        recent_years = [y for y in years if y >= current_year - window_years]

        if not recent_years:
            return 0.0

        total = sum(years[y] for y in recent_years)
        return total / window_years

    def get_acceleration(self, compound: str) -> float:
        """
        Get acceleration (change in velocity).

        Acceleration represents momentum in research attention.
        Positive = research is increasing
        Negative = research is declining
        """
        compound = compound.upper()
        years = self.compound_years.get(compound, {})

        if not years:
            return 0.0

        # Compare last 2 years vs previous 2 years
        current_year = datetime.now().year
        recent = sum(years.get(y, 0) for y in [current_year, current_year - 1])
        prior = sum(years.get(y, 0) for y in [current_year - 2, current_year - 3])

        if prior == 0:
            return float(recent)  # New compound, all acceleration

        return (recent - prior) / 2.0  # Change per year

    def get_jerk(self, compound: str) -> float:
        """
        Get jerk (change in acceleration).

        Jerk represents inflection points - when research attention
        is transitioning from accelerating to decelerating or vice versa.
        High positive jerk = emerging hot topic
        High negative jerk = topic cooling off rapidly
        """
        compound = compound.upper()
        years = self.compound_years.get(compound, {})

        if not years:
            return 0.0

        current_year = datetime.now().year

        # Acceleration for recent period
        recent = sum(years.get(y, 0) for y in [current_year, current_year - 1])
        mid = sum(years.get(y, 0) for y in [current_year - 2, current_year - 3])
        prior = sum(years.get(y, 0) for y in [current_year - 4, current_year - 5])

        acc_recent = (recent - mid) / 2.0
        acc_prior = (mid - prior) / 2.0

        return acc_recent - acc_prior

    def get_content_signals(self, compound: str) -> Dict[str, int]:
        """
        Get content signal counts for a compound.

        Returns counts of health, contamination, and regulatory mentions.
        """
        compound = compound.upper()
        return dict(self.content_signals.get(compound, {}))

    def get_all_metrics(self, compound: str) -> Dict[str, Any]:
        """Get all dynamics metrics for a compound."""
        return {
            "compound": compound.upper(),
            "position": self.get_position(compound),
            "velocity": round(self.get_velocity(compound), 2),
            "acceleration": round(self.get_acceleration(compound), 2),
            "jerk": round(self.get_jerk(compound), 2),
            "content_signals": self.get_content_signals(compound),
            "yearly_counts": dict(self.compound_years.get(compound.upper(), {})),
        }

    def get_compound_ranking(self) -> List[Dict[str, Any]]:
        """Get all compounds ranked by composite risk signal."""
        compounds = list(self.compound_years.keys())

        results = []
        for compound in compounds:
            metrics = self.get_all_metrics(compound)

            # Compute composite score
            pos_norm = min(metrics["position"] / 100, 1.0)  # Normalize to 0-1
            vel_norm = min(metrics["velocity"] / 10, 1.0)
            acc_norm = min(max(metrics["acceleration"] + 5, 0) / 10, 1.0)
            jerk_norm = min(max(metrics["jerk"] + 5, 0) / 10, 1.0)

            content = metrics["content_signals"]
            content_score = (
                content.get("health", 0) * 0.4 +
                content.get("contamination", 0) * 0.3 +
                content.get("regulatory", 0) * 0.3
            )
            content_norm = min(content_score / 10, 1.0)

            composite = (
                0.2 * pos_norm +
                0.3 * vel_norm +
                0.25 * acc_norm +
                0.15 * jerk_norm +
                0.1 * content_norm
            )

            metrics["composite_score"] = round(composite, 3)
            results.append(metrics)

        return sorted(results, key=lambda x: x["composite_score"], reverse=True)
