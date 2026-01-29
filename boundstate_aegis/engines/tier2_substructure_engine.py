#!/usr/bin/env python3
"""
Module: tier2_substructure_engine
Purpose: AEGIS Tier 2 Substructure + Heuristic Rules Engine (Evidence-Correlated).
    Mines the PFAS fate corpus to build substructure-to-endpoint correlation
    rules using SMARTS patterns and algorithmic chain detection. Operates
    on RESOLVED PRECURSORS ONLY, counts UNIQUE PRECURSORS (not edges),
    and reports Wilson score confidence intervals.

    NOT A PREDICTION ENGINE. Returns pattern-based correlations from
    literature with explicit coverage and uncertainty.

    Rev History:
        1.0.0 - Initial Tier 2 engine with hybrid pattern detection,
                precursor-based rule mining, and Wilson CI

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
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel

from boundstate_aegis.config import COMPOUNDS_DIR, EPA_COMPTOX_CSV, PFAS_FATE_V2_JSON

logger = logging.getLogger(__name__)

# RDKit is required for Tier 2
try:
    from rdkit import Chem
    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    logger.warning("RDKit not available. Tier 2 substructure engine disabled.")


# =============================================================================
# CONSTANTS
# =============================================================================

MIN_SUPPORT = 5  # Minimum precursors for a rule to be emitted

# SMARTS for functional groups (vetted for RDKit compatibility)
FUNCTIONAL_GROUP_SMARTS = {
    "carboxylic_acid": "C(=O)[O;H1,-1]",
    "sulfonate": "S(=O)(=O)[O;H1,-1]",
    "sulfonamide": "S(=O)(=O)N",
    "ether_linkage": "[#6]-O-[#6]",
    "fluorinated_ether": "[#6](F)(F)-O-[#6](F)(F)",
    "terminal_oh": "[OH1]",
}

# Pre-compiled SMARTS patterns (populated on first use)
_COMPILED_SMARTS: Dict[str, Any] = {}

# =============================================================================
# PRECURSOR NAME ALIASES
# =============================================================================
# Maps variant/parenthetical names to canonical names already resolved
# by the SMILES resolution chain (manual, enrichment, or EPA).

PRECURSOR_ALIASES: Dict[str, str] = {
    # Parenthetical duplicates
    "Perfluorooctanoic acid (PFOA)": "PFOA",
    "Perfluorooctane sulfonic acid (PFOS)": "PFOS",
    "Perfluorohexanoic acid (PFHxA)": "PFHxA",
    "Perfluorobutanoic acid (PFBA)": "PFBA",
    "Perfluorobutane sulfonic acid (PFBS)": "PFBS",
    "Perfluorononanoic acid (PFNA)": "PFNA",
    "Perfluorodecanoic acid (PFDA)": "PFDA",
    "Trifluoroacetic acid (TFA)": "TFA",
    "Hexafluoropropylene oxide dimer acid (HFPO-DA)": "GenX",
    "GenX (HFPO-DA)": "GenX",
    "Tetracycline (TC)": "tetracycline",
    "Bisphenol A (BPA)": "bisphenol A",
    "COF2 (carbonyl fluoride)": "COF2",
    "CHF3 (fluoroform)": "CHF3",
    "perfluorooctane sulfonamide (FOSA)": "FOSA",
    "CF2 (difluorocarbene)": "CF2O",
    "C5F10O (M6)": "CF2O",
    "C6F11O3 (M4)": "HFPO-DA",
    "N-alkylated perfluoroalkane sulfonamides (FASAs)": "FOSA",
    # Spacing / formatting variants
    "6:2FTS": "6:2 FTS",
    "8:2FTS": "8:2 FTS",
    "6:2FTOH": "6:2 FTOH",
    "8:2FTOH": "8:2 FTOH",
    "6:2FTCA": "5:3 FTCA",
    "FTOH 4:2": "4:2 FTOH",
    "62:FTSA": "6:2 FTS",
    # Abbreviation variants
    "HFPO-DA": "GenX",
    "PFHeA": "PFHxA",
    "RhB": "rhodamine B",
    "PFCA": "PFOA",
    # Acid formula → canonical name
    "C3F7COOH": "PFBA",
    "C4F9COOH": "PFPeA",
    "C2F5COOH": "PFPrA",
}

# =============================================================================
# POLYMER MONOMER SMILES
# =============================================================================
# Monomer/representative structures for fluoropolymer classes,
# following the existing PTFE/PVDF/FEP pattern in tier1 MANUAL_SMILES.

POLYMER_MONOMER_SMILES: Dict[str, str] = {
    "PCTFE": "FC(F)=C(Cl)F",
    "ECTFE": "FC(Cl)=C(F)F",
    "PVDF-HFP": "C(F)(F)=C",
    "PVDF-CTFE": "C(F)(F)=C",
    "CPTFE": "FC(F)=C(Cl)F",
    "PFA": "C(=C(F)F)(OC(F)(F)F)F",
    "FKM rubber": "FC(F)=C(F)F",
    "CF3-terminated PVDF": "C(F)(F)=C",
    # Chemical formulas not in PubChem
    "C7F15OH": "OC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "C7F15COO-": "[O-]C(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "C3F7": "FC(F)(F)C(F)(F)C(F)(F)F",
    "CF3": "FC(F)F",
    "CF3CH3": "CC(F)(F)F",
    "CF3CHF2": "FC(F)C(F)(F)F",
    "CF3OH": "OC(F)(F)F",
    "n-C4F10": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "n-C6F14": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "C6F13COF": "FC(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "C7F15O-": "[O-]C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "C6F13O2COO-": "[O-]C(=O)C(F)(F)OC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "1-C7F14": "FC(F)=C(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    # PFAS abbreviations missed by PubChem
    "PFMOPrA": "OC(=O)C(F)(F)OC(F)(F)F",
    "PFMOBA": "OC(=O)C(F)(F)C(F)(F)OC(F)(F)F",
    "PFOSAmS": "COCCN(C)S(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "bis-FMeSI (NTf2)": "O=S(=O)([N-]S(=O)(=O)C(F)(F)F)C(F)(F)F",
    "bis-FEtSI": "O=S(=O)([N-]S(=O)(=O)C(F)(F)C(F)(F)F)C(F)(F)C(F)(F)F",
    # Radical species → neutral parent
    "n-C4F9 radical": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "C7F15 radical": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "CF3 radical": "FC(F)F",
    "C7F15\u2022": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "\u2022C7F15": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
}

# =============================================================================
# NON-RESOLVABLE PRECURSOR PATTERNS
# =============================================================================
# Regex patterns matching class terms, mixtures, and descriptive names
# that cannot map to a single SMILES. Filtered from the denominator.

NON_RESOLVABLE_PATTERNS: List[str] = [
    # Descriptive / class terms
    r".*fluorinated polymers.*",
    r".*fluoropolymers.*",
    r".*precursors.*",
    r".*compounds in.*",
    r".*-based precursors.*",
    r".*-laden.*",
    r".*containing .*",
    r".*functionalized.*",
    # Mixtures
    r".* and .*",
    r".*\(C\d+-C\d+\).*",
    # Bulk AFFF references
    r".*AFFF.*",
    # Generic plural class terms
    r"^FOSAs$",
    r"^FOSEs$",
    r"^FTACs$",
    r"^FTMACs$",
    r"^FTIs$",
    r"^FTOHs$",
    r"^HFCs$",
    r"^HCFCs$",
    r"^PFSAs$",
    r"^PFSA$",
    r"^PFASs.*$",
    r"^PFAS$",
    r"^diPAPs$",
    r"^PFCA salts$",
    # Environmental matrix references
    r".*biosolids.*",
    r".*waste.*",
    r".*substrate.*",
    r".*microplastics.*",
    r".*coating$",
    # Polymer processing variants (PTFE with additives)
    r"^PTFE with .*",
    r"^PTFE beads$",
    # Generic radical/fragment notation
    r".*fluoroalkyl radicals.*",
    r".*perfluoroalkyl radicals.*",
    r"^perfluoro radicals.*",
    r"^perfluoroalkyl radical.*",
    r".*perfluoroacyl fluorides.*",
    # Generic chain-length notation
    r"^CnF2n\+1O.*",
    r"^-\(CF2-CF2\)n-$",
    r".*copolymers$",
    # Intermediate labels from reaction mechanisms
    r"^INT\d+$",
    r"^IM\d+$",
    r"^S\d+$",
    # Other non-compound entries
    r"^polypropylene$",
    r"^polyethylene$",
    r"^polyethylene terephthalate$",
    r"^polyvinyl chloride$",
    r"^polystyrene$",
    r"^low-density polyethylene$",
    r"^cotton substrate$",
    # Abbreviation plurals that reference classes
    r".*FASAs and FASEs.*",
    r".*bis-FASIs$",
    # Ionic notation with bullet/radical marker
    r".*C6F13O2\u2022$",
    r".*C7F15COO\u2022$",
    r".*C7F15O\u2022$",
    r".*CnF2n\+1O\u2022$",
    r".*hydrofluorocarbons.*",
]

_COMPILED_NR_PATTERNS: Optional[List["re.Pattern[str]"]] = None


def _get_nr_patterns() -> List["re.Pattern[str]"]:
    """Compile and cache non-resolvable regex patterns."""
    global _COMPILED_NR_PATTERNS
    if _COMPILED_NR_PATTERNS is None:
        _COMPILED_NR_PATTERNS = [
            re.compile(p, re.IGNORECASE) for p in NON_RESOLVABLE_PATTERNS
        ]
    return _COMPILED_NR_PATTERNS


def is_resolvable_precursor(name: str) -> bool:
    """Return False for names that are inherently non-resolvable."""
    for pat in _get_nr_patterns():
        if pat.search(name):
            return False
    return True


def _get_compiled_smarts() -> Dict[str, Any]:
    """Compile and cache SMARTS patterns."""
    global _COMPILED_SMARTS
    if not _COMPILED_SMARTS and HAS_RDKIT:
        for name, smarts in FUNCTIONAL_GROUP_SMARTS.items():
            pat = Chem.MolFromSmarts(smarts)
            if pat is None:
                logger.warning("Failed to compile SMARTS for %s: %s", name, smarts)
            else:
                _COMPILED_SMARTS[name] = pat
    return _COMPILED_SMARTS


# Endpoint taxonomy — shared with Tier 1
ENDPOINT_TAXONOMY: Dict[str, List[str]] = {
    "long_chain_acids": [
        "PFOA", "PFNA", "PFDA", "PFUnDA", "PFDoDA",
        "perfluorooctanoic acid",
    ],
    "short_chain_acids": [
        "TFA", "PFBA", "PFPeA", "PFHxA", "PFHpA",
        "trifluoroacetic acid",
    ],
    "sulfonates": [
        "PFOS", "PFHxS", "PFBS",
        "perfluorooctane sulfonic acid",
    ],
    "fluorotelomers": [
        "6:2 FTOH", "8:2 FTOH", "4:2 FTOH", "10:2 FTOH",
        "6:2 FTCA", "8:2 FTCA",
    ],
    "gases": ["HF", "COF2", "CF4", "CO2", "F2", "carbonyl fluoride"],
    "benign": ["H2O", "CO2", "fluoride", "F-", "acetic acid", "formic acid"],
    "radicals": [],
}


def classify_endpoint(product_name: str) -> str:
    """Classify a product into an endpoint bucket."""
    name_lower = product_name.lower()

    for category, members in ENDPOINT_TAXONOMY.items():
        for member in members:
            if member.lower() in name_lower or name_lower in member.lower():
                return category

    # Heuristics for unclassified
    if "radical" in name_lower or "\u2022" in product_name:
        return "radicals"
    if "pfoa" in name_lower or "perfluorooctan" in name_lower:
        return "long_chain_acids"
    if "pfos" in name_lower or "sulfon" in name_lower:
        return "sulfonates"
    if "ftoh" in name_lower or "fluorotelomer" in name_lower:
        return "fluorotelomers"

    return "other"


# =============================================================================
# WILSON CONFIDENCE INTERVAL
# =============================================================================

def wilson_ci(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """
    Wilson score interval for binomial proportion.

    Uses the normal approximation z-value. For alpha=0.05, z=1.96.
    Avoids scipy dependency by using a lookup for common alpha values,
    falling back to the Abramowitz & Stegun rational approximation.
    """
    if n == 0:
        return (0.0, 0.0)

    z = _z_score(alpha)
    p_hat = k / n
    denom = 1 + z ** 2 / n
    center = (p_hat + z ** 2 / (2 * n)) / denom
    margin = z * ((p_hat * (1 - p_hat) + z ** 2 / (4 * n)) / n) ** 0.5 / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _z_score(alpha: float) -> float:
    """
    Return z-score for two-tailed (1 - alpha) confidence.

    Common values hardcoded; otherwise uses rational approximation
    of the inverse normal CDF (Abramowitz & Stegun 26.2.23).
    """
    _Z_LOOKUP = {
        0.01: 2.5758,
        0.05: 1.9600,
        0.10: 1.6449,
    }
    if alpha in _Z_LOOKUP:
        return _Z_LOOKUP[alpha]

    # Rational approximation for probit function
    p = 1 - alpha / 2
    if p <= 0 or p >= 1:
        return 1.96
    t = math.sqrt(-2 * math.log(1 - p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)


# =============================================================================
# ALGORITHMIC FEATURE DETECTION
# =============================================================================

def compute_fluorine_metrics(mol) -> Dict[str, Any]:
    """
    Compute fluorine-related structural metrics for a molecule.

    Returns:
        perfluoro_chain_len_max: longest fluorinated carbon chain
        perfluoro_carbon_count: total carbons with >=2 F
        has_cf3_terminal: bool (carbon with 3 F)
        cf2_count: carbons with exactly 2 F
        f_count: total fluorines
        c_count: total carbons
        f_to_c_ratio: f_count / c_count (0 if no carbons)
    """
    f_count = 0
    c_count = 0
    cf3_found = False
    cf2_count = 0
    perfluoro_carbon_count = 0

    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        if symbol == "F":
            f_count += 1
        elif symbol == "C":
            c_count += 1
            f_neighbors = sum(
                1 for nbr in atom.GetNeighbors() if nbr.GetSymbol() == "F"
            )
            if f_neighbors >= 2:
                perfluoro_carbon_count += 1
            if f_neighbors == 3:
                cf3_found = True
            if f_neighbors == 2:
                cf2_count += 1

    chain_len = _compute_perfluoro_chain_length(mol)

    return {
        "perfluoro_chain_len_max": chain_len,
        "perfluoro_carbon_count": perfluoro_carbon_count,
        "has_cf3_terminal": cf3_found,
        "cf2_count": cf2_count,
        "f_count": f_count,
        "c_count": c_count,
        "f_to_c_ratio": round(f_count / c_count, 3) if c_count > 0 else 0.0,
    }


def _compute_perfluoro_chain_length(mol) -> int:
    """
    Find longest contiguous path of aliphatic carbons where each carbon
    has >= 2 fluorine substituents (i.e., CF2/CF3 units).

    Builds a subgraph of "fluorinated carbons" connected by C-C bonds,
    then finds the longest path in that subgraph via DFS.
    """
    # Identify fluorinated carbons (>= 2 F neighbors)
    fluoro_carbons: Set[int] = set()
    for atom in mol.GetAtoms():
        if atom.GetSymbol() != "C":
            continue
        f_neighbors = sum(
            1 for nbr in atom.GetNeighbors() if nbr.GetSymbol() == "F"
        )
        if f_neighbors >= 2:
            fluoro_carbons.add(atom.GetIdx())

    if not fluoro_carbons:
        return 0

    # Build adjacency for fluorinated carbons connected by C-C bonds
    adj: Dict[int, List[int]] = defaultdict(list)
    for idx in fluoro_carbons:
        atom = mol.GetAtomWithIdx(idx)
        for nbr in atom.GetNeighbors():
            nbr_idx = nbr.GetIdx()
            if nbr_idx in fluoro_carbons:
                adj[idx].append(nbr_idx)

    # Find longest path via DFS from each node
    max_len = 0

    def dfs(node: int, visited: Set[int]) -> int:
        best = 0
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                best = max(best, 1 + dfs(neighbor, visited))
                visited.discard(neighbor)
        return best

    for start in fluoro_carbons:
        length = dfs(start, {start}) + 1  # +1 to count the starting node
        if length > max_len:
            max_len = length

    return max_len


def classify_compound(mol, metrics: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Classify a molecule into structural categories based on
    functional groups and fluorination patterns.

    Returns list of classification labels.
    """
    if metrics is None:
        metrics = compute_fluorine_metrics(mol)

    smarts = _get_compiled_smarts()
    classifications: List[str] = []

    chain_len = metrics["perfluoro_chain_len_max"]
    has_carboxylic = bool(
        "carboxylic_acid" in smarts and mol.HasSubstructMatch(smarts["carboxylic_acid"])
    )
    has_sulfonate = bool(
        "sulfonate" in smarts and mol.HasSubstructMatch(smarts["sulfonate"])
    )
    has_oh = bool(
        "terminal_oh" in smarts and mol.HasSubstructMatch(smarts["terminal_oh"])
    )

    # PFAA: perfluoroalkyl acid (carboxylic + long perfluoro chain)
    if has_carboxylic and chain_len >= 4:
        classifications.append("pfaa")

    # PFSA: perfluoroalkyl sulfonic acid
    if has_sulfonate and chain_len >= 4:
        classifications.append("pfsa")

    # Fluorotelomer: terminal OH with partial fluorination
    if has_oh and not has_carboxylic and chain_len >= 2:
        # Check for non-fluorinated carbon spacer (CH2-CH2 between OH and CF2)
        classifications.append("fluorotelomer")

    # Chain length buckets
    # Note: perfluoro_chain_len counts fluorinated carbons only.
    # "C8 PFAS" (e.g., PFOA) = 7 perfluoro C + 1 COOH C.
    # Convention: long_chain >= 7 perfluoro C (C8+ total).
    if 4 <= chain_len <= 6:
        classifications.append("short_chain")
    elif chain_len >= 7:
        classifications.append("long_chain")

    return classifications


# =============================================================================
# PATTERN DETECTION (UNIFIED)
# =============================================================================

@dataclass
class PatternMatch:
    """A detected structural pattern."""
    pattern_name: str
    pattern_type: str  # 'smarts', 'algorithmic', or 'classification'
    value: Optional[str] = None


def detect_all_patterns(mol) -> List[PatternMatch]:
    """
    Detect all structural patterns in a molecule.

    Combines SMARTS functional group matches, algorithmic fluorine
    metrics, and compound-level classifications.
    """
    matches: List[PatternMatch] = []
    smarts = _get_compiled_smarts()

    # A) SMARTS functional groups
    for name, pattern in smarts.items():
        if mol.HasSubstructMatch(pattern):
            matches.append(PatternMatch(
                pattern_name=name,
                pattern_type="smarts",
            ))

    # B) Algorithmic features
    metrics = compute_fluorine_metrics(mol)
    chain_len = metrics["perfluoro_chain_len_max"]

    if chain_len > 0:
        # Chain length bucket pattern
        # perfluoro_chain_len counts fluorinated carbons only.
        # C8 PFAS (PFOA) = 7 perfluoro C + 1 COOH C, so >= 7 is "C8+".
        if chain_len >= 7:
            matches.append(PatternMatch(
                pattern_name="perfluoro_chain_c8plus",
                pattern_type="algorithmic",
                value=f"chain_length={chain_len}",
            ))
        elif chain_len >= 4:
            matches.append(PatternMatch(
                pattern_name="perfluoro_chain_c4_c6",
                pattern_type="algorithmic",
                value=f"chain_length={chain_len}",
            ))

    if metrics["has_cf3_terminal"]:
        matches.append(PatternMatch(
            pattern_name="cf3_terminal",
            pattern_type="algorithmic",
        ))

    if metrics["f_to_c_ratio"] > 1.5:
        matches.append(PatternMatch(
            pattern_name="high_f_to_c_ratio",
            pattern_type="algorithmic",
            value=f"ratio={metrics['f_to_c_ratio']}",
        ))

    # C) Compound classifications
    classifications = classify_compound(mol, metrics)
    for cls in classifications:
        matches.append(PatternMatch(
            pattern_name=cls,
            pattern_type="classification",
        ))

    return matches


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SubstructureRule(BaseModel):
    """A mined substructure-to-endpoint correlation rule."""
    pattern_name: str
    endpoint_bucket: str
    n_precursors: int
    k_with_endpoint: int
    confidence: float
    ci_low: float
    ci_high: float
    example_precursors: List[str]
    example_products: List[str]


class PatternMatchResponse(BaseModel):
    """API representation of a detected pattern."""
    pattern_name: str
    pattern_type: str
    value: Optional[str] = None


class EndpointCorrelation(BaseModel):
    """An endpoint correlation result for a query compound."""
    endpoint_bucket: str
    confidence: float
    ci_low: float
    ci_high: float
    n_precursors: int
    k_with_endpoint: int
    supporting_patterns: List[str]
    example_products: List[str]


class Tier2PredictRequest(BaseModel):
    """Request body for Tier 2 prediction."""
    smiles: str


class Tier2PredictResponse(BaseModel):
    """Full Tier 2 prediction response."""
    query_smiles: str
    patterns_detected: List[PatternMatchResponse]
    fluorine_metrics: Dict[str, Any]
    endpoint_correlations: List[EndpointCorrelation]
    coverage_info: Dict[str, Any]
    disclaimer: str = (
        "Pattern-based correlation from literature corpus (353 papers). "
        "Confidence is observed frequency among resolved precursors, "
        "not a physical or causal prediction. Validate experimentally."
    )


class PatternDefinition(BaseModel):
    """Definition of a pattern used in detection."""
    name: str
    pattern_type: str
    smarts: Optional[str] = None
    description: str


class CoverageReport(BaseModel):
    """Preflight coverage report for the Tier 2 engine."""
    total_precursors: int
    resolvable_precursors: int
    resolved_precursors: int
    resolution_rate: float  # resolved / resolvable
    total_pathways: int
    pathways_with_resolved_precursor: int
    unresolved_precursors: List[Dict[str, Any]]  # [{name, pathway_count}]
    non_resolvable_count: int
    non_resolvable_examples: List[str]
    patterns_with_support: Dict[str, int]
    patterns_insufficient_support: Dict[str, int]


# =============================================================================
# INTERNAL STATS TRACKING
# =============================================================================

@dataclass
class _PatternStats:
    """Internal: tracks precursor counts per pattern during mining."""
    precursor_set: Set[str] = field(default_factory=set)
    endpoint_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Track example precursors per endpoint for rule output
    endpoint_precursors: Dict[str, List[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    endpoint_products: Dict[str, List[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    @property
    def n_precursors(self) -> int:
        return len(self.precursor_set)


# =============================================================================
# TIER 2 ENGINE
# =============================================================================

class Tier2Engine:
    """
    Tier 2 Substructure Rules Engine.

    Mines the PFAS fate corpus to build substructure-to-endpoint
    correlation rules. Operates on resolved precursors only,
    counts unique precursors (not edges), and reports Wilson
    score confidence intervals.
    """

    def __init__(
        self,
        fate_json_path: Optional[Path] = None,
        epa_csv_path: Optional[Path] = None,
        min_support: int = MIN_SUPPORT,
    ):
        if not HAS_RDKIT:
            raise RuntimeError(
                "RDKit is required for Tier 2 engine. "
                "Install with: pip install rdkit-pypi"
            )

        self.min_support = min_support
        self.rules: List[SubstructureRule] = []
        self._coverage: Optional[CoverageReport] = None

        # Internal state
        self._fate_data: Dict[str, Any] = {}
        self._precursor_smiles: Dict[str, str] = {}
        self._unresolved: Dict[str, int] = {}  # name -> pathway_count
        self._pattern_stats: Dict[str, _PatternStats] = defaultdict(_PatternStats)
        self._enrichment_smiles: Dict[str, str] = {}

        # Paths
        self._fate_path = fate_json_path or PFAS_FATE_V2_JSON
        self._epa_path = epa_csv_path or EPA_COMPTOX_CSV

        # Load enrichment file if available
        self._load_enrichment()

        # Load and mine
        self._tier1_engine = None
        self._mine_corpus()

    def _load_enrichment(self) -> None:
        """Load SMILES enrichment file if it exists."""
        enrichment_path = COMPOUNDS_DIR / "smiles_enrichment.json"
        if not enrichment_path.exists():
            return
        try:
            with open(enrichment_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, info in data.get("compounds", {}).items():
                smiles = info.get("smiles")
                if smiles and info.get("validated"):
                    self._enrichment_smiles[name] = smiles
            logger.info(
                "Tier 2: Loaded %d SMILES from enrichment file", len(self._enrichment_smiles)
            )
        except Exception as e:
            logger.warning("Failed to load enrichment file: %s", e)

    def _get_tier1_engine(self):
        """Lazy-load the Tier 1 engine for SMILES resolution."""
        if self._tier1_engine is None:
            try:
                from boundstate_aegis.engines.tier1_engine import AEGISTier1Engine
                self._tier1_engine = AEGISTier1Engine(
                    epa_csv_path=self._epa_path,
                    fate_json_path=self._fate_path,
                )
            except Exception as e:
                logger.warning("Could not load Tier 1 engine for resolution: %s", e)
        return self._tier1_engine

    def _resolve_smiles(self, name: str) -> Optional[str]:
        """
        Resolve a precursor name to SMILES.

        Resolution order:
        1. Alias map (canonical name redirect)
        2. Polymer monomer / manual SMILES
        3. Enrichment file (PubChem/CompTox batch results)
        4. Tier 1 engine resolve_smiles (manual → fate → EPA)
        """
        # 1. Check alias map — redirect to canonical name
        canonical = PRECURSOR_ALIASES.get(name, name)

        # 2. Check polymer monomer / manual SMILES
        if canonical in POLYMER_MONOMER_SMILES:
            return POLYMER_MONOMER_SMILES[canonical]
        if name in POLYMER_MONOMER_SMILES:
            return POLYMER_MONOMER_SMILES[name]

        # 3. Enrichment file
        if canonical in self._enrichment_smiles:
            return self._enrichment_smiles[canonical]
        if name in self._enrichment_smiles:
            return self._enrichment_smiles[name]

        # 4. Tier 1 engine (manual → fate → EPA)
        engine = self._get_tier1_engine()
        if engine:
            smiles = engine.resolve_smiles(canonical)
            if smiles:
                return smiles
            if canonical != name:
                return engine.resolve_smiles(name)
        return None

    def _mine_corpus(self) -> None:
        """
        Mine the pathway corpus to build substructure rules.

        Steps:
        1. Load pfas_fate_v2.json
        2. Build precursor -> SMILES map (track unresolved)
        3. Build precursor -> endpoint_buckets map (unique precursors)
        4. Detect patterns on each resolved precursor
        5. Generate rules where n >= MIN_SUPPORT
        """
        logger.info("Tier 2: Mining corpus from %s", self._fate_path)

        # 1. Load fate data
        if not self._fate_path.exists():
            logger.error("Fate JSON not found: %s", self._fate_path)
            self._build_empty_coverage()
            return

        with open(self._fate_path, "r", encoding="utf-8") as f:
            self._fate_data = json.load(f)

        pathways = self._fate_data.get("pathways", [])
        total_pathways = len(pathways)

        # 2. Collect unique precursors and their endpoint buckets
        precursor_endpoints: Dict[str, Set[str]] = defaultdict(set)
        precursor_products: Dict[str, Dict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        precursor_pathway_count: Dict[str, int] = defaultdict(int)

        for p in pathways:
            precursor = p.get("precursor", "")
            product = p.get("product", "")
            if not precursor or not product:
                continue

            bucket = classify_endpoint(product)
            precursor_endpoints[precursor].add(bucket)
            precursor_products[precursor][bucket].add(product)
            precursor_pathway_count[precursor] += 1

        all_precursors = set(precursor_endpoints.keys())
        total_precursors = len(all_precursors)

        # 3. Partition into resolvable vs non-resolvable, then resolve
        non_resolvable: List[str] = []
        resolvable_precursors: Set[str] = set()

        for precursor in all_precursors:
            if is_resolvable_precursor(precursor):
                resolvable_precursors.add(precursor)
            else:
                non_resolvable.append(precursor)

        resolved_count = 0
        unresolved: Dict[str, int] = {}

        for precursor in resolvable_precursors:
            smiles = self._resolve_smiles(precursor)
            if smiles:
                self._precursor_smiles[precursor] = smiles
                resolved_count += 1
            else:
                unresolved[precursor] = precursor_pathway_count[precursor]

        self._unresolved = unresolved
        self._non_resolvable = non_resolvable

        n_resolvable = len(resolvable_precursors)
        logger.info(
            "Tier 2: Resolved %d / %d resolvable precursors (%.1f%%) "
            "[%d non-resolvable filtered]",
            resolved_count,
            n_resolvable,
            100 * resolved_count / n_resolvable if n_resolvable else 0,
            len(non_resolvable),
        )

        # 4. For each resolved precursor, detect patterns and update stats
        pathways_with_resolved = 0
        for precursor, smiles in self._precursor_smiles.items():
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.warning("RDKit parse failed for %s: %s", precursor, smiles)
                continue

            patterns = detect_all_patterns(mol)
            endpoints = precursor_endpoints[precursor]

            # Count pathways with resolved precursor
            pathways_with_resolved += precursor_pathway_count[precursor]

            # Update stats: PRECURSOR-BASED, not edge-based
            for pm in patterns:
                stats = self._pattern_stats[pm.pattern_name]
                stats.precursor_set.add(precursor)
                for endpoint in endpoints:
                    stats.endpoint_counts[endpoint] += 1
                    # Track examples (limit storage)
                    if len(stats.endpoint_precursors[endpoint]) < 10:
                        if precursor not in stats.endpoint_precursors[endpoint]:
                            stats.endpoint_precursors[endpoint].append(precursor)
                    # Track example products
                    for prod in precursor_products[precursor].get(endpoint, set()):
                        if len(stats.endpoint_products[endpoint]) < 10:
                            if prod not in stats.endpoint_products[endpoint]:
                                stats.endpoint_products[endpoint].append(prod)

        # 5. Generate rules where n >= min_support
        self.rules = []
        patterns_with_support: Dict[str, int] = {}
        patterns_insufficient: Dict[str, int] = {}

        for pattern_name, stats in self._pattern_stats.items():
            n = stats.n_precursors
            if n < self.min_support:
                patterns_insufficient[pattern_name] = n
                continue

            patterns_with_support[pattern_name] = n

            for endpoint, k in stats.endpoint_counts.items():
                confidence = k / n
                ci_low, ci_high = wilson_ci(k, n)

                self.rules.append(SubstructureRule(
                    pattern_name=pattern_name,
                    endpoint_bucket=endpoint,
                    n_precursors=n,
                    k_with_endpoint=k,
                    confidence=round(confidence, 4),
                    ci_low=round(ci_low, 4),
                    ci_high=round(ci_high, 4),
                    example_precursors=stats.endpoint_precursors[endpoint][:5],
                    example_products=stats.endpoint_products[endpoint][:5],
                ))

        # Sort rules by confidence descending
        self.rules.sort(key=lambda r: r.confidence, reverse=True)

        # 6. Build coverage report
        # Sort unresolved by pathway count descending
        unresolved_sorted = sorted(
            unresolved.items(), key=lambda x: x[1], reverse=True
        )
        n_resolvable = len(resolvable_precursors)

        self._coverage = CoverageReport(
            total_precursors=total_precursors,
            resolvable_precursors=n_resolvable,
            resolved_precursors=resolved_count,
            resolution_rate=round(
                resolved_count / n_resolvable if n_resolvable else 0, 4
            ),
            total_pathways=total_pathways,
            pathways_with_resolved_precursor=pathways_with_resolved,
            unresolved_precursors=[
                {"name": name, "pathway_count": count}
                for name, count in unresolved_sorted[:20]
            ],
            non_resolvable_count=len(non_resolvable),
            non_resolvable_examples=sorted(non_resolvable)[:10],
            patterns_with_support=patterns_with_support,
            patterns_insufficient_support=patterns_insufficient,
        )

        logger.info(
            "Tier 2: Mined %d rules from %d patterns (min_support=%d)",
            len(self.rules),
            len(patterns_with_support),
            self.min_support,
        )
        self._log_preflight()

    def _build_empty_coverage(self) -> None:
        """Build an empty coverage report when data is unavailable."""
        self._coverage = CoverageReport(
            total_precursors=0,
            resolvable_precursors=0,
            resolved_precursors=0,
            resolution_rate=0.0,
            total_pathways=0,
            pathways_with_resolved_precursor=0,
            unresolved_precursors=[],
            non_resolvable_count=0,
            non_resolvable_examples=[],
            patterns_with_support={},
            patterns_insufficient_support={},
        )

    def _log_preflight(self) -> None:
        """Log the preflight report to the console."""
        cov = self._coverage
        if cov is None:
            return

        lines = [
            "",
            "=" * 50,
            "TIER 2 PREFLIGHT REPORT",
            "=" * 50,
            f"Total precursors:    {cov.total_precursors}",
            f"Non-resolvable:      {cov.non_resolvable_count} (filtered)",
            f"Resolvable:          {cov.resolvable_precursors}",
            f"Resolved:            {cov.resolved_precursors} / "
            f"{cov.resolvable_precursors} ({cov.resolution_rate:.0%})",
            f"Resolved pathways:   {cov.pathways_with_resolved_precursor} / "
            f"{cov.total_pathways}",
            "",
        ]

        if cov.unresolved_precursors:
            lines.append(f"TOP {len(cov.unresolved_precursors)} UNRESOLVED PRECURSORS:")
            for i, entry in enumerate(cov.unresolved_precursors, 1):
                lines.append(
                    f"  {i:2d}. \"{entry['name']}\" "
                    f"({entry['pathway_count']} pathways)"
                )
            lines.append("")

        if cov.patterns_with_support:
            lines.append(f"PATTERNS WITH SUPPORT >= {self.min_support}:")
            for name, n in sorted(
                cov.patterns_with_support.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(f"  - {name}: n={n}")
            lines.append("")

        if cov.patterns_insufficient_support:
            lines.append("PATTERNS WITH INSUFFICIENT SUPPORT:")
            for name, n in sorted(
                cov.patterns_insufficient_support.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(
                    f"  - {name}: n={n} (need {self.min_support - n} more)"
                )

        lines.append("=" * 50)
        logger.info("\n".join(lines))

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def predict_endpoints(self, smiles: str) -> Tier2PredictResponse:
        """
        Given a SMILES string, detect patterns and return correlated
        endpoint buckets with confidence intervals.
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return Tier2PredictResponse(
                query_smiles=smiles,
                patterns_detected=[],
                fluorine_metrics={},
                endpoint_correlations=[],
                coverage_info={"error": "Invalid SMILES"},
            )

        # Detect patterns
        patterns = detect_all_patterns(mol)
        metrics = compute_fluorine_metrics(mol)

        # Look up rules for matched patterns
        matched_pattern_names = {pm.pattern_name for pm in patterns}
        endpoint_results = self._aggregate_rules(matched_pattern_names)

        return Tier2PredictResponse(
            query_smiles=smiles,
            patterns_detected=[
                PatternMatchResponse(
                    pattern_name=pm.pattern_name,
                    pattern_type=pm.pattern_type,
                    value=pm.value,
                )
                for pm in patterns
            ],
            fluorine_metrics=metrics,
            endpoint_correlations=endpoint_results,
            coverage_info=self._get_coverage_stats(),
        )

    def _aggregate_rules(
        self, pattern_names: Set[str]
    ) -> List[EndpointCorrelation]:
        """
        Aggregate rules across matched patterns for each endpoint.

        For each endpoint bucket, select the rule with the best support
        (highest n_precursors) among all matching patterns. This avoids
        double-counting while giving the most grounded estimate.
        """
        # Group rules by endpoint
        endpoint_best: Dict[str, Dict[str, Any]] = {}

        for rule in self.rules:
            if rule.pattern_name not in pattern_names:
                continue

            ep = rule.endpoint_bucket
            if ep not in endpoint_best:
                endpoint_best[ep] = {
                    "confidence": rule.confidence,
                    "ci_low": rule.ci_low,
                    "ci_high": rule.ci_high,
                    "n_precursors": rule.n_precursors,
                    "k_with_endpoint": rule.k_with_endpoint,
                    "supporting_patterns": [rule.pattern_name],
                    "example_products": list(rule.example_products),
                }
            else:
                entry = endpoint_best[ep]
                # Use rule with higher support as primary
                if rule.n_precursors > entry["n_precursors"]:
                    entry["confidence"] = rule.confidence
                    entry["ci_low"] = rule.ci_low
                    entry["ci_high"] = rule.ci_high
                    entry["n_precursors"] = rule.n_precursors
                    entry["k_with_endpoint"] = rule.k_with_endpoint
                if rule.pattern_name not in entry["supporting_patterns"]:
                    entry["supporting_patterns"].append(rule.pattern_name)
                # Merge example products
                for prod in rule.example_products:
                    if prod not in entry["example_products"]:
                        entry["example_products"].append(prod)
                entry["example_products"] = entry["example_products"][:5]

        # Convert to response models, sorted by confidence
        results = [
            EndpointCorrelation(
                endpoint_bucket=ep,
                **data,
            )
            for ep, data in endpoint_best.items()
        ]
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def _get_coverage_stats(self) -> Dict[str, Any]:
        """Return coverage stats for inclusion in predict responses."""
        cov = self._coverage
        if cov is None:
            return {}
        return {
            "resolved_precursors": cov.resolved_precursors,
            "resolvable_precursors": cov.resolvable_precursors,
            "total_precursors": cov.total_precursors,
            "non_resolvable_count": cov.non_resolvable_count,
            "resolution_rate": cov.resolution_rate,
            "rules_count": len(self.rules),
        }

    def get_coverage(self) -> CoverageReport:
        """Return the full coverage report."""
        if self._coverage is None:
            self._build_empty_coverage()
        return self._coverage  # type: ignore[return-value]

    def get_rules(
        self, offset: int = 0, limit: int = 50
    ) -> Tuple[List[SubstructureRule], int]:
        """
        Return paginated rules.

        Returns (rules_page, total_count).
        """
        total = len(self.rules)
        page = self.rules[offset : offset + limit]
        return page, total

    def get_patterns(self) -> List[PatternDefinition]:
        """Return definitions of all patterns used in detection."""
        definitions: List[PatternDefinition] = []

        # SMARTS patterns
        for name, smarts in FUNCTIONAL_GROUP_SMARTS.items():
            definitions.append(PatternDefinition(
                name=name,
                pattern_type="smarts",
                smarts=smarts,
                description=f"SMARTS match for {name.replace('_', ' ')}",
            ))

        # Algorithmic patterns
        algorithmic_patterns = {
            "perfluoro_chain_c8plus": "Perfluorinated carbon chain >= 7 (C8+ total, long chain)",
            "perfluoro_chain_c4_c6": "Perfluorinated carbon chain 4-6 (short chain)",
            "cf3_terminal": "Terminal CF3 group detected",
            "high_f_to_c_ratio": "Fluorine to carbon ratio > 1.5",
        }
        for name, desc in algorithmic_patterns.items():
            definitions.append(PatternDefinition(
                name=name,
                pattern_type="algorithmic",
                description=desc,
            ))

        # Classification patterns
        classification_patterns = {
            "pfaa": "Perfluoroalkyl acid (carboxylic acid + perfluoro chain >= 4)",
            "pfsa": "Perfluoroalkyl sulfonic acid (sulfonate + perfluoro chain >= 4)",
            "fluorotelomer": "Fluorotelomer (terminal OH + partial fluorination)",
            "short_chain": "Short chain PFAS (perfluoro chain 4-6 carbons)",
            "long_chain": "Long chain PFAS (perfluoro chain >= 7 carbons, C8+ total)",
        }
        for name, desc in classification_patterns.items():
            definitions.append(PatternDefinition(
                name=name,
                pattern_type="classification",
                description=desc,
            ))

        return definitions
