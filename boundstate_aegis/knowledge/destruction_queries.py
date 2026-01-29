#!/usr/bin/env python3
"""
Module: destruction_queries
Purpose: Query functions for destruction technology lookup.
    Provides find_destruction_options() to recommend technologies for
    specific compounds, and get_chemours_capability_gap() for IP analysis.

    Rev History:
        1.0.0 - Initial destruction query functions

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>

"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

from boundstate_aegis.models.destruction_technology import (
    DestructionTechnology,
    DestructionCapability,
    DestructionIneffective,
    CostEstimate,
    ChemoursPosition,
    TechnologyRecommendation,
)
from boundstate_aegis.config import DATA_DIR

logger = logging.getLogger(__name__)

# Cache for loaded technologies
_TECHNOLOGIES_CACHE: Optional[Dict[str, DestructionTechnology]] = None


def _load_technologies() -> Dict[str, DestructionTechnology]:
    """Load destruction technologies from YAML file."""
    global _TECHNOLOGIES_CACHE

    if _TECHNOLOGIES_CACHE is not None:
        return _TECHNOLOGIES_CACHE

    if yaml is None:
        raise RuntimeError("PyYAML is required for destruction technology lookup")

    tech_path = DATA_DIR / "destruction_technologies.yaml"
    if not tech_path.exists():
        logger.warning("Destruction technologies file not found: %s", tech_path)
        return {}

    with tech_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    technologies = {}
    for tech_data in data.get("technologies", []):
        tech_id = tech_data.get("id")
        if not tech_id:
            continue

        # Parse effective_for
        effective_for = []
        for eff in tech_data.get("effective_for", []):
            effective_for.append(DestructionCapability(
                compound_class=eff.get("compound_class", ""),
                includes=eff.get("includes", []),
                phase=eff.get("phase", "aqueous"),
                min_dre=float(eff.get("min_dre", 0.99)),
                conditions=eff.get("conditions"),
                notes=eff.get("notes"),
            ))

        # Parse ineffective_for
        ineffective_for = []
        for ineff in tech_data.get("ineffective_for", []):
            ineffective_for.append(DestructionIneffective(
                compound_class=ineff.get("compound_class", ""),
                reason=ineff.get("reason", ""),
                notes=ineff.get("notes"),
            ))

        # Parse costs
        costs_data = tech_data.get("costs")
        costs = None
        if costs_data:
            costs = CostEstimate(
                capex_estimate=costs_data.get("capex_estimate"),
                opex_estimate=costs_data.get("opex_estimate"),
                notes=costs_data.get("notes"),
            )

        # Parse chemours_position
        chem_data = tech_data.get("chemours_position")
        chemours_position = None
        if chem_data:
            chemours_position = ChemoursPosition(
                owns_technology=chem_data.get("owns_technology", False),
                owns_ip=chem_data.get("owns_ip", False),
                must_license_from=chem_data.get("must_license_from"),
                forced_buyer=chem_data.get("forced_buyer", False),
                location=chem_data.get("location"),
                limitation=chem_data.get("limitation"),
                notes=chem_data.get("notes"),
            )

        technologies[tech_id] = DestructionTechnology(
            id=tech_id,
            name=tech_data.get("name", tech_id),
            acronym=tech_data.get("acronym"),
            mechanism=tech_data.get("mechanism", "unknown"),
            developer=tech_data.get("developer"),
            developers=tech_data.get("developers", []),
            commercial_operator=tech_data.get("commercial_operator"),
            commercial_operators=tech_data.get("commercial_operators", []),
            ip_holder=tech_data.get("ip_holder"),
            trl=tech_data.get("trl", 1),
            effective_for=effective_for,
            ineffective_for=ineffective_for,
            products=tech_data.get("products"),
            challenges=tech_data.get("challenges", []),
            evidence=tech_data.get("evidence"),
            costs=costs,
            chemours_position=chemours_position,
        )

    _TECHNOLOGIES_CACHE = technologies
    logger.info("Loaded %d destruction technologies", len(technologies))
    return technologies


def get_all_technologies() -> List[DestructionTechnology]:
    """Get all loaded destruction technologies."""
    return list(_load_technologies().values())


def get_technology(tech_id: str) -> Optional[DestructionTechnology]:
    """Get a specific technology by ID."""
    return _load_technologies().get(tech_id)


def find_destruction_options(
    compound: str,
    phase: str = "aqueous",
    min_trl: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find viable destruction technologies for a given compound and phase.

    Args:
        compound: Target compound (e.g., "TFA", "PFOA")
        phase: Matrix phase ("aqueous", "gas", "solid", "slurry")
        min_trl: Minimum Technology Readiness Level (default 5)

    Returns:
        List of technology options sorted by TRL (highest first), each containing:
        - technology: DestructionTechnology object
        - dre: Destruction/Removal Efficiency
        - conditions: Operating conditions
        - viable: True if effective, False if ineffective
        - reason: Why it's viable or not
    """
    technologies = _load_technologies()
    options = []

    compound_upper = compound.upper()

    for tech in technologies.values():
        # Check TRL threshold
        if tech.trl < min_trl:
            continue

        # Check if ineffective
        ineffective_reason = tech.is_ineffective_for(compound_upper)
        if ineffective_reason:
            options.append({
                "technology": tech,
                "technology_id": tech.id,
                "technology_name": tech.name,
                "trl": tech.trl,
                "dre": None,
                "conditions": None,
                "viable": False,
                "reason": ineffective_reason,
            })
            continue

        # Check if effective
        if tech.can_destroy(compound_upper, phase):
            dre = tech.get_dre_for(compound_upper, phase)
            conditions = tech.get_conditions_for(compound_upper, phase)
            options.append({
                "technology": tech,
                "technology_id": tech.id,
                "technology_name": tech.name,
                "trl": tech.trl,
                "dre": dre,
                "conditions": conditions,
                "viable": True,
                "reason": f"Effective for {compound_upper} in {phase} phase",
            })

    # Sort by viability (viable first), then by TRL (highest first), then by DRE
    options.sort(key=lambda x: (
        not x["viable"],  # Viable first
        -x["trl"],  # Higher TRL first
        -(x["dre"] or 0),  # Higher DRE first
    ))

    return options


def get_recommended_technology(
    compound: str,
    phase: str = "aqueous",
) -> TechnologyRecommendation:
    """
    Get the recommended destruction technology for a compound.

    Args:
        compound: Target compound
        phase: Matrix phase

    Returns:
        TechnologyRecommendation with recommended tech and alternatives
    """
    options = find_destruction_options(compound, phase, min_trl=1)

    viable = [o for o in options if o["viable"]]
    not_viable = [o for o in options if not o["viable"]]

    if not viable:
        return TechnologyRecommendation(
            compound=compound,
            phase=phase,
            recommended_technology="none",
            recommendation_reason=f"No viable destruction technology found for {compound} in {phase} phase",
            alternatives=[],
            not_viable=[{"technology": o["technology_name"], "reason": o["reason"]} for o in not_viable],
        )

    # Best option is first (already sorted)
    best = viable[0]
    tech = best["technology"]

    return TechnologyRecommendation(
        compound=compound,
        phase=phase,
        recommended_technology=tech.name,
        recommendation_reason=best["reason"],
        dre=best["dre"],
        conditions=best["conditions"],
        alternatives=[
            {
                "technology": o["technology_name"],
                "trl": o["trl"],
                "dre": o["dre"],
            }
            for o in viable[1:4]  # Up to 3 alternatives
        ],
        not_viable=[
            {"technology": o["technology_name"], "reason": o["reason"]}
            for o in not_viable
        ],
        chemours_gap=_get_chemours_gap_text(tech),
    )


def _get_chemours_gap_text(tech: DestructionTechnology) -> Optional[str]:
    """Generate text describing Chemours' capability gap."""
    if tech.chemours_position is None:
        return "Chemours IP position unknown"

    if tech.chemours_position.owns_technology:
        return None  # No gap

    parts = []
    if tech.chemours_position.must_license_from:
        parts.append(f"Must license from: {tech.chemours_position.must_license_from}")
    if tech.chemours_position.forced_buyer:
        parts.append("Forced buyer status: TRUE")
    if tech.chemours_position.limitation:
        parts.append(f"Limitation: {tech.chemours_position.limitation}")

    return "; ".join(parts) if parts else "Chemours does not own this technology"


def get_chemours_capability_gap(compound: str, phase: str = "aqueous") -> Dict[str, Any]:
    """
    Analyze what Chemours has vs what's needed for destroying a compound.

    Args:
        compound: Target compound
        phase: Matrix phase

    Returns:
        Dict with:
        - has: Technologies Chemours owns
        - needs: Technologies required for this compound
        - gap: Description of the capability gap
        - must_license_from: Who Chemours must license from
        - forced_buyer: Whether Chemours is a forced buyer
    """
    technologies = _load_technologies()
    options = find_destruction_options(compound, phase)

    has = []
    needs = []
    license_from = []

    for tech in technologies.values():
        if tech.chemours_position and tech.chemours_position.owns_technology:
            has.append({
                "technology": tech.name,
                "limitation": tech.chemours_position.limitation,
            })

    for opt in options:
        if not opt["viable"]:
            continue
        tech = opt["technology"]
        needs.append({
            "technology": tech.name,
            "trl": tech.trl,
            "dre": opt["dre"],
        })
        if tech.chemours_must_license():
            license_from.append({
                "technology": tech.name,
                "from": tech.chemours_position.must_license_from if tech.chemours_position else "Unknown",
            })

    # Determine if there's a gap
    has_effective = False
    for h in has:
        for n in needs:
            if h["technology"] == n["technology"]:
                has_effective = True
                break

    gap_description = None
    if not has_effective and needs:
        gap_description = f"Chemours lacks {compound} destruction capability in {phase} phase"

    return {
        "compound": compound,
        "phase": phase,
        "has": has,
        "needs": needs,
        "gap": gap_description,
        "must_license_from": license_from,
        "forced_buyer": bool(license_from),
    }


def clear_cache() -> None:
    """Clear the technologies cache (for testing/reload)."""
    global _TECHNOLOGIES_CACHE
    _TECHNOLOGIES_CACHE = None
