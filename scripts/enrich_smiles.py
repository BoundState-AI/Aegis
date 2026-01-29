#!/usr/bin/env python3
"""
Module: enrich_smiles
Purpose: Batch SMILES enrichment for unresolved PFAS precursors.
    Queries PubChem and CompTox APIs to resolve precursor names/CAS
    numbers to canonical SMILES. Validates all results with RDKit.

    Rev History:
        1.0.0 - Initial batch enrichment pipeline

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the workspace root is on sys.path for package resolution
_WORKSPACE_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

import requests
from rdkit import Chem, RDLogger

# Suppress RDKit warnings
RDLogger.DisableLog("rdApp.*")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PACKAGE_ROOT / "data"
EVIDENCE_DIR = DATA_DIR / "evidence"
COMPOUNDS_DIR = DATA_DIR / "compounds"

PFAS_FATE_V2_JSON = EVIDENCE_DIR / "pfas_fate_v2.json"
COMPOUND_REGISTRY = COMPOUNDS_DIR / "compound_registry_clean.json"
OUTPUT_PATH = COMPOUNDS_DIR / "smiles_enrichment.json"

# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
COMPTOX_SEARCH = "https://comptox.epa.gov/dashboard-api/ccdapp1/search/chemical/equal"
COMPTOX_DETAIL = "https://comptox.epa.gov/dashboard-api/ccdapp1/chemical"

REQUEST_TIMEOUT = 15  # seconds
RATE_LIMIT_DELAY = 0.25  # seconds between API calls


# ---------------------------------------------------------------------------
# Local resolution: compound_registry_clean.json
# ---------------------------------------------------------------------------


def build_registry_lookup() -> Dict[str, str]:
    """
    Build a name/alias -> canonical SMILES map from compound_registry_clean.json.

    This is free (no API call) and should be checked first.
    """
    lookup: Dict[str, str] = {}
    if not COMPOUND_REGISTRY.exists():
        logger.warning("Compound registry not found: %s", COMPOUND_REGISTRY)
        return lookup

    with open(COMPOUND_REGISTRY, "r", encoding="utf-8") as f:
        data = json.load(f)

    compounds = data.get("compounds", {})
    for _key, entry in compounds.items():
        smiles = entry.get("smiles_canonical")
        if not smiles:
            continue
        # Index by primary name and all aliases
        primary = entry.get("primary_name", "")
        if primary:
            lookup[primary] = smiles
            lookup[primary.upper()] = smiles
        for alias in entry.get("aliases", []):
            lookup[alias] = smiles
            lookup[alias.upper()] = smiles

    logger.info("Registry lookup: %d entries from %d compounds", len(lookup), len(compounds))
    return lookup


# ---------------------------------------------------------------------------
# CAS number extraction
# ---------------------------------------------------------------------------


def build_cas_map() -> Dict[str, str]:
    """
    Build a precursor name -> CAS number map from all available sources.

    Sources checked:
      1. pfas_fate_v2.json compounds dict
      2. compound_registry_clean.json (via aliases)
    """
    cas_map: Dict[str, str] = {}

    # Source 1: pfas_fate_v2.json compounds
    if PFAS_FATE_V2_JSON.exists():
        with open(PFAS_FATE_V2_JSON, "r", encoding="utf-8") as f:
            fate_data = json.load(f)
        for name, comp in fate_data.get("compounds", {}).items():
            cas = comp.get("cas")
            if cas:
                cas_map[name] = cas

    # Source 2: compound_registry_clean.json
    if COMPOUND_REGISTRY.exists():
        with open(COMPOUND_REGISTRY, "r", encoding="utf-8") as f:
            reg_data = json.load(f)
        for _key, entry in reg_data.get("compounds", {}).items():
            cas = entry.get("cas")
            if not cas:
                continue
            primary = entry.get("primary_name", "")
            if primary:
                cas_map[primary] = cas
            for alias in entry.get("aliases", []):
                cas_map[alias] = cas

    logger.info("CAS map: %d entries", len(cas_map))
    return cas_map


# ---------------------------------------------------------------------------
# PubChem API
# ---------------------------------------------------------------------------


def lookup_pubchem_by_name(name: str) -> Optional[str]:
    """Query PubChem for canonical SMILES by compound name."""
    try:
        url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(name)}/property/ConnectivitySMILES/JSON"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        props = resp.json().get("PropertyTable", {}).get("Properties", [])
        if props:
            return props[0].get("ConnectivitySMILES")
    except Exception as e:
        logger.debug("PubChem name lookup failed for %s: %s", name, e)
    return None


def lookup_pubchem_by_cas(cas: str) -> Optional[str]:
    """Query PubChem for canonical SMILES by CAS number."""
    try:
        url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(cas)}/property/ConnectivitySMILES/JSON"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        props = resp.json().get("PropertyTable", {}).get("Properties", [])
        if props:
            return props[0].get("ConnectivitySMILES")
    except Exception as e:
        logger.debug("PubChem CAS lookup failed for %s: %s", cas, e)
    return None


# ---------------------------------------------------------------------------
# CompTox API
# ---------------------------------------------------------------------------


def _comptox_dtxsid_for_query(query: str) -> Optional[str]:
    """Search CompTox and return the DTXSID of the first match."""
    try:
        url = f"{COMPTOX_SEARCH}/{requests.utils.quote(query)}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        results = resp.json()
        if results and isinstance(results, list):
            return results[0].get("dtxsid")
    except Exception as e:
        logger.debug("CompTox search failed for %s: %s", query, e)
    return None


def _comptox_smiles_for_dtxsid(dtxsid: str) -> Optional[str]:
    """Fetch SMILES for a DTXSID from CompTox."""
    try:
        url = f"{COMPTOX_DETAIL}/{dtxsid}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("smiles") or data.get("qsarReadySmiles")
    except Exception as e:
        logger.debug("CompTox detail failed for %s: %s", dtxsid, e)
    return None


def lookup_comptox_by_name(name: str) -> Optional[str]:
    """Query CompTox for SMILES by compound name."""
    dtxsid = _comptox_dtxsid_for_query(name)
    if dtxsid:
        return _comptox_smiles_for_dtxsid(dtxsid)
    return None


def lookup_comptox_by_cas(cas: str) -> Optional[str]:
    """Query CompTox for SMILES by CAS number."""
    dtxsid = _comptox_dtxsid_for_query(cas)
    if dtxsid:
        return _comptox_smiles_for_dtxsid(dtxsid)
    return None


# ---------------------------------------------------------------------------
# SMILES validation
# ---------------------------------------------------------------------------


def validate_smiles(smiles: str) -> bool:
    """Validate a SMILES string with RDKit."""
    if not smiles:
        return False
    mol = Chem.MolFromSmiles(smiles)
    return mol is not None


# ---------------------------------------------------------------------------
# Batch enrichment pipeline
# ---------------------------------------------------------------------------


def resolve_single(
    name: str,
    cas: Optional[str],
    registry_lookup: Dict[str, str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Attempt to resolve a precursor name to SMILES.

    Resolution order:
      1. Local compound registry (no API call)
      2. PubChem by CAS
      3. PubChem by name
      4. CompTox by CAS
      5. CompTox by name

    Returns (smiles, source) or (None, None).
    """
    # 1. Check local registry
    smiles = registry_lookup.get(name) or registry_lookup.get(name.upper())
    if smiles and validate_smiles(smiles):
        return smiles, "compound_registry"

    # 2. PubChem by CAS
    if cas:
        smiles = lookup_pubchem_by_cas(cas)
        if smiles and validate_smiles(smiles):
            return smiles, "pubchem_cas"
        time.sleep(RATE_LIMIT_DELAY)

    # 3. PubChem by name
    smiles = lookup_pubchem_by_name(name)
    if smiles and validate_smiles(smiles):
        return smiles, "pubchem_name"
    time.sleep(RATE_LIMIT_DELAY)

    # 4. CompTox by CAS
    if cas:
        smiles = lookup_comptox_by_cas(cas)
        if smiles and validate_smiles(smiles):
            return smiles, "comptox_cas"
        time.sleep(RATE_LIMIT_DELAY)

    # 5. CompTox by name
    smiles = lookup_comptox_by_name(name)
    if smiles and validate_smiles(smiles):
        return smiles, "comptox_name"
    time.sleep(RATE_LIMIT_DELAY)

    return None, None


def enrich_all_precursors(
    unresolved: List[Dict[str, Any]],
    registry_lookup: Dict[str, str],
    cas_map: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    """
    Run the enrichment pipeline on all unresolved precursors.

    Parameters
    ----------
    unresolved : list of dicts
        Each dict has at least 'name' and 'pathway_count' keys.
    registry_lookup : dict
        Name/alias -> canonical SMILES from compound registry.
    cas_map : dict
        Name -> CAS number from all available sources.

    Returns
    -------
    dict
        Mapping of precursor name -> enrichment record.
    """
    results: Dict[str, Dict[str, Any]] = {}
    total = len(unresolved)

    for i, item in enumerate(unresolved, 1):
        name = item["name"]
        cas = cas_map.get(name)

        smiles, source = resolve_single(name, cas, registry_lookup)

        if smiles:
            results[name] = {
                "smiles": smiles,
                "source": source,
                "cas": cas,
                "validated": True,
                "pathway_count": item.get("pathway_count", 0),
            }
            display = smiles if len(smiles) <= 40 else smiles[:37] + "..."
            logger.info("[%d/%d] RESOLVED  %s  (%s) -> %s", i, total, name, source, display)
        else:
            logger.info("[%d/%d] NOT FOUND %s", i, total, name)

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def save_enrichment(
    results: Dict[str, Dict[str, Any]],
    total_queried: int,
    output_path: Path = OUTPUT_PATH,
) -> None:
    """Save enrichment results with metadata."""
    source_counts: Dict[str, int] = {}
    for r in results.values():
        src = r["source"]
        source_counts[src] = source_counts.get(src, 0) + 1

    output = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "total_queried": total_queried,
            "total_resolved": len(results),
            "resolution_rate": round(len(results) / total_queried, 4) if total_queried else 0,
            "sources": source_counts,
        },
        "compounds": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    logger.info("Saved %d enriched compounds to %s", len(results), output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  AEGIS Batch SMILES Enrichment Pipeline")
    print("=" * 60)
    print()

    # ---- 1. Get unresolved precursors from Tier 2 engine -----------------
    logger.info("Loading Tier 2 engine to identify unresolved precursors...")
    from boundstate_aegis.engines.tier2_substructure_engine import Tier2Engine

    engine = Tier2Engine()
    coverage = engine.get_coverage()

    # Access the full unresolved dict (CoverageReport only has top 20)
    all_unresolved = engine._unresolved  # {name: pathway_count}
    unresolved_list = [
        {"name": name, "pathway_count": count}
        for name, count in sorted(all_unresolved.items(), key=lambda x: -x[1])
    ]

    print(f"Current resolution: {coverage.resolved_precursors}/{coverage.total_precursors} "
          f"({coverage.resolution_rate:.1%})")
    print(f"Unresolved: {len(unresolved_list)}")
    print()

    if not unresolved_list:
        print("All precursors already resolved. Nothing to do.")
        return

    # ---- 2. Build lookup tables ------------------------------------------
    logger.info("Building local lookup tables...")
    registry_lookup = build_registry_lookup()
    cas_map = build_cas_map()

    # ---- 3. Run enrichment -----------------------------------------------
    print(f"Querying PubChem + CompTox for {len(unresolved_list)} precursors...")
    print()

    results = enrich_all_precursors(
        unresolved=unresolved_list,
        registry_lookup=registry_lookup,
        cas_map=cas_map,
    )

    # ---- 4. Save results -------------------------------------------------
    save_enrichment(results, total_queried=len(unresolved_list))

    # ---- 5. Summary ------------------------------------------------------
    print()
    print("=" * 60)
    print(f"  Resolved: {len(results)}/{len(unresolved_list)} "
          f"previously-unresolved precursors")
    print()

    source_counts: Dict[str, int] = {}
    for r in results.values():
        src = r["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"    {src:25s} {count:4d}")

    projected_total = coverage.resolved_precursors + len(results)
    projected_rate = projected_total / coverage.total_precursors if coverage.total_precursors else 0.0
    print()
    print(f"  Projected resolution: {projected_total}/{coverage.total_precursors} ({projected_rate:.1%})")
    print("=" * 60)

    # ---- 6. Verify by reloading Tier 2 -----------------------------------
    print()
    logger.info("Rebuilding Tier 2 engine with enriched data...")
    engine2 = Tier2Engine()
    coverage2 = engine2.get_coverage()

    improvement = coverage2.resolved_precursors - coverage.resolved_precursors
    print(f"NEW resolution: {coverage2.resolved_precursors}/{coverage2.total_precursors} "
          f"({coverage2.resolution_rate:.1%})")
    print(f"Improvement: +{improvement} precursors")


if __name__ == "__main__":
    main()
