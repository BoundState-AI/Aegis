#!/usr/bin/env python3
"""
Module: fate_route
Purpose: PFAS Fate Explorer API endpoints for degradation pathway visualization.
    Provides /api/v1/pfas/* endpoints for the FateExplorer UI.
    Loads degradation pathway data from extracted literature and knowledge graph.

    Rev History:
        1.0.0 - Initial fate explorer routes

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
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, Query
from pydantic import BaseModel
from rdkit import Chem

from boundstate_aegis.knowledge.graph_builder import build_graph, PFASKnowledgeGraph
from boundstate_aegis.config import (
    DEGRADATION_PATHWAYS_EXTRACTED,
    PFAS_LIT_SUMMARY,
    PFAS_FATE_V2_JSON,
    LITERATURE_PAPER_COUNT,
    CONFIDENCE_MAPPING,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for graph and database
_graph_cache = None
_kg_cache: Optional[PFASKnowledgeGraph] = None
_database_cache: Optional[Dict[str, Dict[str, Any]]] = None

# SMILES lookup cache for fluorine detection
_smiles_cache: Optional[Dict[str, str]] = None


def _load_smiles_lookup() -> Dict[str, str]:
    """Load SMILES from enrichment and registry files for fluorine detection."""
    global _smiles_cache
    if _smiles_cache is not None:
        return _smiles_cache

    _smiles_cache = {}
    data_dir = Path(__file__).parent.parent.parent / "data"

    # Load smiles_enrichment.json (primary source - PubChem resolved)
    enrichment_path = data_dir / "compounds" / "smiles_enrichment.json"
    if enrichment_path.exists():
        try:
            data = json.loads(enrichment_path.read_text(encoding="utf-8"))
            for name, info in data.get("compounds", {}).items():
                if info.get("smiles"):
                    _smiles_cache[name.upper()] = info["smiles"]
        except Exception as e:
            logger.warning(f"Failed to load smiles_enrichment.json: {e}")

    # Load compound_registry_clean.json
    registry_path = data_dir / "compounds" / "compound_registry_clean.json"
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            for inchikey, info in data.get("compounds", {}).items():
                smiles = info.get("smiles_canonical") or info.get("smiles_raw")
                if smiles:
                    name = info.get("primary_name", "").upper()
                    if name and name not in _smiles_cache:
                        _smiles_cache[name] = smiles
                    for alias in info.get("aliases", []):
                        if alias and alias.upper() not in _smiles_cache:
                            _smiles_cache[alias.upper()] = smiles
        except Exception as e:
            logger.warning(f"Failed to load compound_registry_clean.json: {e}")

    logger.info(f"Loaded {len(_smiles_cache)} SMILES entries for fluorine detection")
    return _smiles_cache


def _has_fluorine_rdkit(smiles: str) -> Optional[bool]:
    """Check if SMILES contains fluorine atoms using RDKit. Returns None if invalid."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return any(atom.GetAtomicNum() == 9 for atom in mol.GetAtoms())
    except Exception:
        return None


# Intermediate label pattern (IM2, INT3, S1, etc.)
_INTERMEDIATE_PATTERN = re.compile(r'^(IM\d+|INT\d+|S\d+)$', re.IGNORECASE)


def _is_fluorinated_compound(name: str) -> bool:
    """
    Determine if a compound is fluorinated using RDKit chemistry with string fallback.

    Priority:
    1. Exclude intermediate labels (IM2, INT3, S1, etc.)
    2. Check RDKit if SMILES available
    3. Fall back to string pattern matching
    """
    # Reject intermediate/vague labels
    if _INTERMEDIATE_PATTERN.match(name.strip()):
        return False

    # Try RDKit-based check first
    smiles_lookup = _load_smiles_lookup()
    smiles = smiles_lookup.get(name.upper())
    if smiles:
        result = _has_fluorine_rdkit(smiles)
        if result is not None:
            return result

    # Fallback: string-based fluorine pattern matching
    name_lower = name.lower()

    # Known non-fluorinated patterns (exclude these)
    non_fluor_patterns = [
        'bisphenol', 'carbamazepine', 'ciprofloxacin', 'ibuprofen',
        'norfloxacin', 'sulfamethoxazole', 'tetracycline', 'congo red',
        'methyl orange', 'methylene blue', 'rhodamine', 'pyrene',
        'polyethylene', 'polypropylene', 'polystyrene', 'polyvinyl',
        'hmx', 'rdx', 'parathion', 'benzothiazole', 'hexachlorocyclohexane',
        'malic acid', 'boron', 'b2o3', 'cotton', 'tbbpa', 'aucl4',
        'peroxymonosulfate', 'persulfate', 'sulfate radical', ' hcl',
        'reactive yellow', 'cobaltocenium', 'silicone rubber',
        'dichlorophen', 'waste polypropylene', 'low-density polyethylene',
    ]
    for pattern in non_fluor_patterns:
        if pattern in name_lower:
            return False

    # Fluorinated patterns (positive indicators)
    fluor_patterns = [
        'pf', 'ptfe', 'pvdf', 'pfa', 'fep', 'etfe', 'pctfe', 'ectfe',
        'fluor', 'ft', 'hfp', 'vdf', 'genx', 'hfpo', 'tfa', 'cof2',
        'cf', 'c2f', 'c3f', 'c4f', 'c5f', 'c6f', 'c7f', 'c8f', 'c9f',
        'afff', 'fkm', 'fos', 'fasa', 'fase', 'pfpe', 'pfepe', 'ppve',
        'hfc', 'hfo', 'chf', ':2 f', 'dipap', 'monopap', 'fasi',
    ]
    for pattern in fluor_patterns:
        if pattern in name_lower:
            return True

    # Default: reject if no clear fluorine indicator
    return False


def get_graph():
    """Get or build the pathway graph (returns the underlying NetworkX MultiDiGraph)."""
    global _graph_cache, _kg_cache
    if _graph_cache is None:
        _kg_cache = build_graph()
        _graph_cache = _kg_cache.graph
        logger.info(f"Built knowledge graph with {len(_graph_cache.nodes)} nodes")
    return _graph_cache


def get_knowledge_graph() -> PFASKnowledgeGraph:
    """Get the PFASKnowledgeGraph wrapper."""
    global _kg_cache
    if _kg_cache is None:
        get_graph()  # This populates _kg_cache
    return _kg_cache


def _normalize_confidence(conf_value: Any) -> float:
    """Convert confidence value to float."""
    if isinstance(conf_value, (int, float)):
        return float(conf_value)
    if isinstance(conf_value, str):
        return CONFIDENCE_MAPPING.get(conf_value.lower(), 0.5)
    return 0.5



def _load_pathways_from_v2_json() -> Dict[str, List[Dict[str, Any]]]:
    """Load pathways from V2 curated extraction (732 pathways, 261 precursors)."""
    pathways: Dict[str, List[Dict[str, Any]]] = {}

    if not PFAS_FATE_V2_JSON.exists():
        logger.warning("V2 curated data not found, using legacy sources only")
        return pathways

    try:
        with open(PFAS_FATE_V2_JSON, encoding="utf-8") as f:
            data = json.load(f)

        for pathway in data.get("pathways", []):
            precursor = pathway.get("precursor", "").upper()
            if not precursor:
                continue

            if precursor not in pathways:
                pathways[precursor] = []

            # Handle null mechanism with fallback
            mechanism = pathway.get("mechanism") or "thermal_decomposition"

            # Build temp_range string from V2 structured data
            temp_min = None
            temp_max = None
            temp_range_arr = pathway.get("temp_c_range")
            if temp_range_arr and len(temp_range_arr) >= 2:
                temp_min, temp_max = temp_range_arr[0], temp_range_arr[1]

            if temp_min is not None and temp_max is not None:
                if temp_min == temp_max:
                    temp_range = f"{int(temp_min)}°C"
                else:
                    temp_range = f"{int(temp_min)}-{int(temp_max)}°C"
            elif pathway.get("temp_c_median"):
                temp_range = f"~{int(pathway['temp_c_median'])}°C"
            elif pathway.get("temp_bucket") and pathway["temp_bucket"] != "unknown":
                bucket_map = {
                    "ambient": "20-30°C",
                    "low": "50-100°C",
                    "medium": "100-400°C",
                    "high": "400-800°C",
                    "extreme": ">800°C",
                }
                temp_range = bucket_map.get(pathway["temp_bucket"], "N/A")
            else:
                temp_range = "N/A"

            pathways[precursor].append({
                "child": pathway.get("product", "").upper(),
                "confidence": pathway.get("evidence_score", 0.6),
                "mechanism": mechanism,
                "temp_range": temp_range,
                "atmosphere": "air",
                "citations": pathway.get("source_dois", []),
                "observation_count": pathway.get("observation_count", 1),
            })

        logger.info(f"Loaded {sum(len(v) for v in pathways.values())} pathways for {len(pathways)} compounds from V2")
    except Exception as e:
        logger.error(f"Failed to load V2 JSON: {e}")

    return pathways


def _build_pfas_database() -> Dict[str, Dict[str, Any]]:
    """Build PFAS database from V2 curated extraction (732 pathways from 353 papers)."""
    database: Dict[str, Dict[str, Any]] = {}

    # Load from V2 curated extraction - single source of truth
    v2_pathways = _load_pathways_from_v2_json()

    for compound, pathways_list in v2_pathways.items():
        degradation_products = pathways_list

        # Determine compound type
        compound_type = "fluoropolymer"
        is_pfas = False
        is_regulated = False

        compound_lower = compound.lower()
        if any(x in compound_lower for x in ["pfoa", "pfos", "pfna", "pfda", "genx", "pfhxs"]):
            compound_type = "pfas_legacy"
            is_pfas = True
            is_regulated = True
        elif any(x in compound_lower for x in ["pfba", "pfpea", "pfhxa", "pfhpa", "tfa"]):
            compound_type = "pfas_short_chain"
            is_pfas = True
        elif any(x in compound_lower for x in ["ptfe", "pvdf", "pfa", "fep", "etfe"]):
            compound_type = "fluoropolymer"
        elif any(x in compound_lower for x in ["hfo", "hfc", "r-"]):
            compound_type = "refrigerant"

        database[compound] = {
            "type": compound_type,
            "full_name": compound,
            "is_pfas": is_pfas,
            "is_regulated": is_regulated,
            "degradation_products": degradation_products,
        }

    logger.info(f"Built PFAS database with {len(database)} compounds")
    return database


def get_pfas_database() -> Dict[str, Dict[str, Any]]:
    """Get or build PFAS database (cached)."""
    global _database_cache
    if _database_cache is None:
        _database_cache = _build_pfas_database()

        # Log fluorine filter statistics
        total = len([n for n, d in _database_cache.items() if d.get("degradation_products")])
        fluorinated = len([n for n, d in _database_cache.items()
                          if d.get("degradation_products") and _is_fluorinated_compound(n)])
        logger.info(f"Compound filter: {total} total -> {fluorinated} fluorinated ({total - fluorinated} removed)")

    return _database_cache




class GraphSummary(BaseModel):
    """Summary statistics for the knowledge graph."""
    total_nodes: int
    total_edges: int
    parent_compounds: int
    endpoint_compounds: int
    haiku_records: int


class ParentsResponse(BaseModel):
    """List of parent compounds."""
    parents: List[str]


class Transformation(BaseModel):
    """A single degradation transformation."""
    parent: str
    child: str
    observations: int
    score: float
    temp_range: str
    atmosphere: str
    degradation_types: List[str]
    hazard_level: Optional[str]
    is_regulated: bool
    source_count: int
    citations: List[str] = []


class FateQueryResponse(BaseModel):
    """Response for fate query."""
    query: str
    total_transformations: int
    transformations: List[Transformation]
    compounds_involved: List[str]
    compound_found: bool = True


@router.get("/summary", response_model=GraphSummary)
async def get_summary() -> GraphSummary:
    """Get summary statistics for the PFAS knowledge graph."""
    database = get_pfas_database()

    # Use comprehensive database for accurate counts
    parents = [name for name, data in database.items()
               if data.get("degradation_products") and not data.get("is_endpoint")]
    endpoints = [name for name, data in database.items()
                 if data.get("is_endpoint") or not data.get("degradation_products")]

    # Count total transformations
    total_edges = sum(
        len(data.get("degradation_products", []))
        for data in database.values()
    )

    return GraphSummary(
        total_nodes=len(database),
        total_edges=total_edges,
        parent_compounds=len(parents),
        endpoint_compounds=len(endpoints),
        haiku_records=LITERATURE_PAPER_COUNT,
    )


@router.get("/parents", response_model=ParentsResponse)
async def get_parents() -> ParentsResponse:
    """Get list of fluorinated parent compounds that have degradation pathways."""
    database = get_pfas_database()

    # Get fluorinated compounds with degradation products (parents)
    parents = []
    for name, data in database.items():
        products = data.get("degradation_products", [])
        if products and not data.get("is_endpoint"):
            # Only include fluorinated compounds
            if _is_fluorinated_compound(name):
                parents.append(name)

    # Sort by number of degradation products (most first), then alphabetically
    parents.sort(key=lambda n: (-len(database[n].get("degradation_products", [])), n))

    logger.info(f"Returning {len(parents)} fluorinated parent compounds")
    return ParentsResponse(parents=parents)


def _parse_temp_range(temp_str: str) -> tuple:
    """Parse temperature range string into (min, max) tuple."""
    if not temp_str or temp_str == "N/A":
        return (None, None)

    temp_str = temp_str.replace("°C", "").strip()

    if temp_str.startswith(">"):
        try:
            return (float(temp_str[1:]), None)
        except ValueError:
            return (None, None)
    elif temp_str.startswith("<") or temp_str.startswith("≤"):
        try:
            return (None, float(temp_str[1:]))
        except ValueError:
            return (None, None)
    elif temp_str.startswith("≥"):
        try:
            return (float(temp_str[1:]), None)
        except ValueError:
            return (None, None)
    elif "-" in temp_str:
        parts = temp_str.split("-")
        try:
            return (float(parts[0]), float(parts[1]))
        except (ValueError, IndexError):
            return (None, None)
    elif temp_str.lower() == "ambient":
        return (20, 40)

    # Handle single temperature value (e.g., "500" from "500°C")
    try:
        temp = float(temp_str)
        return (temp, temp)
    except ValueError:
        return (None, None)


@router.get("/fate", response_model=FateQueryResponse)
async def query_fate(
    parent: str = Query(..., description="Parent compound to query"),
    temp_min: int = Query(0, description="Minimum temperature (°C)"),
    temp_max: int = Query(1000, description="Maximum temperature (°C)"),
    atmosphere: Optional[str] = Query(None, description="Atmosphere filter"),
    min_observations: int = Query(1, description="Minimum observation count"),
) -> FateQueryResponse:
    """Query degradation pathways for a parent compound."""
    database = get_pfas_database()
    transformations = []
    compounds = set([parent])

    # Look up in our comprehensive database first
    parent_upper = parent.upper()
    parent_data = database.get(parent_upper) or database.get(parent)

    # Track if compound exists in database (will also check graph below)
    compound_in_database = parent_data is not None

    if parent_data:
        for product in parent_data.get("degradation_products", []):
            child = product["child"]
            compounds.add(child)

            # Parse temperature range
            product_temp_range = product.get("temp_range", "N/A")
            prod_min, prod_max = _parse_temp_range(product_temp_range)

            # Apply temperature filter
            # If user specified a real temp range (not default 0-1000), exclude unknown-temp pathways
            user_filtered_temp = (temp_min > 0 or temp_max < 1000)
            if prod_min is None and prod_max is None and user_filtered_temp:
                continue
            if prod_min is not None and prod_min > temp_max:
                continue
            if prod_max is not None and prod_max < temp_min:
                continue

            # Apply atmosphere filter
            product_atmosphere = product.get("atmosphere", "unknown")
            if atmosphere and atmosphere != "any":
                if product_atmosphere.lower() != atmosphere.lower():
                    continue

            # Get mechanism
            mechanism = product.get("mechanism", "thermal")

            # Check if child is regulated
            child_data = database.get(child, {})
            is_regulated = child_data.get("is_regulated", False)
            if not is_regulated:
                child_lower = child.lower()
                is_regulated = any(pfas in child_lower for pfas in ["pfoa", "pfos", "pfna", "pfda", "genx", "pfhxs"])

            # Determine hazard level
            hazard_level = None
            if is_regulated:
                hazard_level = "HIGH"
            elif child.upper() in ["TFA", "HF", "COF2"]:
                hazard_level = "MEDIUM"
            elif child.upper() in ["CF4", "C2F6", "CO2", "H2O", "C3F8"]:
                hazard_level = "LOW"

            transformations.append(Transformation(
                parent=parent_upper,
                child=child,
                observations=product.get("observation_count", 1),
                score=product.get("confidence", 0.8),
                temp_range=product_temp_range,
                atmosphere=product_atmosphere,
                degradation_types=[mechanism],
                hazard_level=hazard_level,
                is_regulated=is_regulated,
                source_count=len(product.get("citations", [])) or product.get("observation_count", 1),
                citations=product.get("citations", []),
            ))

    # Also check graph for any additional pathways not in database
    graph = get_graph()
    compound_in_graph = parent in graph or parent_upper in graph
    if compound_in_graph:
        graph_parent = parent if parent in graph else parent_upper
        for _, child, key, data in graph.out_edges(graph_parent, keys=True, data=True):
            # Skip if already added from database
            if any(t.child == child for t in transformations):
                continue

            compounds.add(child)

            min_t = data.get("min_temp_c")
            max_t = data.get("max_temp_c")

            if min_t is not None and max_t is not None:
                if max_t < temp_min or min_t > temp_max:
                    continue
                t_range = f"{min_t:.0f}-{max_t:.0f}°C"
            elif min_t is not None:
                if min_t > temp_max:
                    continue
                t_range = f"≥{min_t:.0f}°C"
            elif max_t is not None:
                if max_t < temp_min:
                    continue
                t_range = f"≤{max_t:.0f}°C"
            else:
                # No temp data - skip if user applied a temp filter
                if temp_min > 0 or temp_max < 1000:
                    continue
                t_range = "N/A"

            edge_atmosphere = data.get("atmosphere") or "unknown"
            if atmosphere and atmosphere != "any":
                if edge_atmosphere.lower() != atmosphere.lower():
                    continue

            mechanism = data.get("mechanism", "unknown")
            child_lower = child.lower()
            is_regulated = any(pfas in child_lower for pfas in ["pfoa", "pfos", "pfna", "pfda", "genx"])

            hazard_level = None
            if is_regulated:
                hazard_level = "HIGH"
            elif "tfa" in child_lower or "hf" in child_lower:
                hazard_level = "MEDIUM"
            elif any(x in child_lower for x in ["cf4", "c2f6", "co2", "h2o"]):
                hazard_level = "LOW"

            evidence_refs = data.get("evidence_refs", [])
            dois = [ref.get("doi", "") for ref in evidence_refs if ref.get("doi")]
            transformations.append(Transformation(
                parent=graph_parent,
                child=child,
                observations=1,
                score=data.get("confidence", 0.8),
                temp_range=t_range,
                atmosphere=edge_atmosphere,
                degradation_types=[mechanism],
                hazard_level=hazard_level,
                is_regulated=is_regulated,
                source_count=len(evidence_refs) or 1,
                citations=dois,
            ))

    # Sort by score descending
    transformations.sort(key=lambda t: t.score, reverse=True)

    return FateQueryResponse(
        query=f"{parent_upper} at {temp_min}-{temp_max}°C",
        total_transformations=len(transformations),
        transformations=transformations,
        compounds_involved=list(compounds),
        compound_found=compound_in_database or compound_in_graph,
    )
