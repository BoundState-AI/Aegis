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
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, Query
from pydantic import BaseModel

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


def _load_pathways_from_yaml() -> Dict[str, List[Dict[str, Any]]]:
    """Load degradation pathways from extracted YAML."""
    pathways: Dict[str, List[Dict[str, Any]]] = {}

    if DEGRADATION_PATHWAYS_EXTRACTED.exists():
        try:
            with open(DEGRADATION_PATHWAYS_EXTRACTED, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "degradation_pathways" in data:
                for parent, pathway_list in data["degradation_pathways"].items():
                    parent_upper = parent.upper()
                    if parent_upper not in pathways:
                        pathways[parent_upper] = []

                    for pathway in pathway_list:
                        for product in pathway.get("products", []):
                            pathways[parent_upper].append({
                                "child": product,
                                "confidence": _normalize_confidence(pathway.get("confidence", 0.6)),
                                "mechanism": pathway.get("mechanisms", ["thermal"])[0] if pathway.get("mechanisms") else "thermal",
                                "temp_range": pathway.get("trigger", "N/A") or "N/A",
                                "atmosphere": "air",
                                "citations": pathway.get("citations", []),
                            })

            logger.info(f"Loaded pathways for {len(pathways)} compounds from YAML")
        except Exception as e:
            logger.error(f"Failed to load pathways YAML: {e}")

    return pathways


def _load_pathways_from_lit_summary() -> Dict[str, List[Dict[str, Any]]]:
    """Load pathways from literature summary JSON."""
    pathways: Dict[str, List[Dict[str, Any]]] = {}

    if PFAS_LIT_SUMMARY.exists():
        try:
            with open(PFAS_LIT_SUMMARY, encoding="utf-8") as f:
                raw = json.load(f)

            # Handle both legacy flat list and new {metadata, evidence} schema
            if isinstance(raw, dict):
                records = raw.get("evidence", [])
            elif isinstance(raw, list):
                records = raw
            else:
                records = []

            for record in records:
                if not isinstance(record, dict):
                    continue

                # Support both legacy (polymer/pathway) and new (precursor/product) schemas
                polymer = (record.get("polymer") or record.get("precursor") or "").upper()
                if not polymer:
                    continue

                product = None
                # Legacy format: "PTFE → TFA"
                pathway_str = record.get("pathway", "")
                if pathway_str and "→" in pathway_str:
                    parts = pathway_str.split("→")
                    if len(parts) >= 2:
                        product = parts[-1].strip()
                # New format: direct product field
                if not product:
                    product = record.get("product", "")
                if not product:
                    continue

                if polymer not in pathways:
                    pathways[polymer] = []

                mechanism = record.get("mechanism") or (
                    record.get("mechanisms", ["thermal"])[0] if record.get("mechanisms") else "thermal"
                )

                # Build temp_range from new schema fields
                temp_range = "N/A"
                temp_c = record.get("temperature_c")
                temp_range_arr = record.get("temperature_range_c")
                if temp_range_arr and len(temp_range_arr) >= 2 and temp_range_arr[0] is not None:
                    temp_range = f"{int(temp_range_arr[0])}-{int(temp_range_arr[1])}°C"
                elif temp_c is not None:
                    temp_range = f"{int(temp_c)}°C"

                refs = record.get("references", [])
                if not refs:
                    doi = record.get("doi", "")
                    refs = [doi] if doi else []

                pathways[polymer].append({
                    "child": product,
                    "confidence": _normalize_confidence(record.get("confidence", "low")),
                    "mechanism": mechanism,
                    "temp_range": temp_range,
                    "atmosphere": record.get("atmosphere") or "air",
                    "citations": refs,
                })

            logger.info(f"Loaded pathways for {len(pathways)} polymers from literature summary")
        except Exception as e:
            logger.error(f"Failed to load literature summary: {e}")

    return pathways


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
    """Build PFAS database from YAML and JSON sources."""
    database: Dict[str, Dict[str, Any]] = {}

    # Load from V2 curated extraction (PRIMARY - highest quality)
    v2_pathways = _load_pathways_from_v2_json()

    # Load from extracted YAML (legacy)
    yaml_pathways = _load_pathways_from_yaml()

    # Load from literature summary (legacy backup)
    lit_pathways = _load_pathways_from_lit_summary()

    # Merge pathways - V2 takes precedence, then YAML, then lit
    all_compounds = set(v2_pathways.keys()) | set(yaml_pathways.keys()) | set(lit_pathways.keys())

    for compound in all_compounds:
        v2_list = v2_pathways.get(compound, [])
        yaml_list = yaml_pathways.get(compound, [])
        lit_list = lit_pathways.get(compound, [])

        # Deduplicate by child compound, keeping highest confidence
        # V2 first (highest quality), then YAML, then lit
        products_dict: Dict[str, Dict[str, Any]] = {}
        for pathway in v2_list + yaml_list + lit_list:
            child = pathway["child"]
            if child not in products_dict or pathway["confidence"] > products_dict[child]["confidence"]:
                products_dict[child] = pathway

        degradation_products = list(products_dict.values())

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
        # Merge with fallback data for key compounds not in extracted data
        for name, data in FALLBACK_DATABASE.items():
            if name not in _database_cache:
                _database_cache[name] = data
    return _database_cache


# Minimal fallback for critical compounds not in extracted data
FALLBACK_DATABASE: Dict[str, Dict[str, Any]] = {
    # Fluoropolymers (Parent Materials)
    "PTFE": {
        "type": "fluoropolymer",
        "full_name": "Polytetrafluoroethylene",
        "common_names": ["Teflon"],
        "degradation_products": [
            {"child": "TFA", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.92},
            {"child": "HF", "temp_range": "400-800°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.95},
            {"child": "COF2", "temp_range": "450-600°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.88},
            {"child": "CF4", "temp_range": "500-900°C", "atmosphere": "inert", "mechanism": "pyrolysis", "confidence": 0.85},
            {"child": "C2F6", "temp_range": "500-900°C", "atmosphere": "inert", "mechanism": "pyrolysis", "confidence": 0.80},
        ],
    },
    "PVDF": {
        "type": "fluoropolymer",
        "full_name": "Polyvinylidene fluoride",
        "common_names": ["Kynar"],
        "degradation_products": [
            {"child": "HF", "temp_range": "350-500°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.90},
            {"child": "VDF", "temp_range": "400-600°C", "atmosphere": "inert", "mechanism": "depolymerization", "confidence": 0.75},
        ],
    },
    "PFA": {
        "type": "fluoropolymer",
        "full_name": "Perfluoroalkoxy alkane",
        "common_names": ["Teflon PFA"],
        "degradation_products": [
            {"child": "PFOA", "temp_range": "350-500°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.85},
            {"child": "TFA", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.88},
            {"child": "HF", "temp_range": "400-700°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.92},
        ],
    },
    "FEP": {
        "type": "fluoropolymer",
        "full_name": "Fluorinated ethylene propylene",
        "common_names": ["Teflon FEP"],
        "degradation_products": [
            {"child": "TFA", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.85},
            {"child": "HF", "temp_range": "400-700°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.90},
            {"child": "CF4", "temp_range": "500-800°C", "atmosphere": "inert", "mechanism": "pyrolysis", "confidence": 0.78},
        ],
    },
    "ETFE": {
        "type": "fluoropolymer",
        "full_name": "Ethylene tetrafluoroethylene",
        "common_names": ["Tefzel"],
        "degradation_products": [
            {"child": "HF", "temp_range": "350-550°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.88},
            {"child": "TFA", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.75},
        ],
    },
    "ECTFE": {
        "type": "fluoropolymer",
        "full_name": "Ethylene chlorotrifluoroethylene",
        "common_names": ["Halar"],
        "degradation_products": [
            {"child": "HF", "temp_range": "350-550°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.85},
            {"child": "HCl", "temp_range": "350-500°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.82},
        ],
    },
    "PCTFE": {
        "type": "fluoropolymer",
        "full_name": "Polychlorotrifluoroethylene",
        "common_names": ["Neoflon", "Kel-F"],
        "degradation_products": [
            {"child": "HF", "temp_range": "350-550°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.88},
            {"child": "HCl", "temp_range": "350-500°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.85},
        ],
    },
    "FFKM": {
        "type": "fluoropolymer",
        "full_name": "Perfluoroelastomer",
        "common_names": ["Kalrez", "Chemraz"],
        "degradation_products": [
            {"child": "HF", "temp_range": "300-450°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.90},
            {"child": "TFA", "temp_range": "350-500°C", "atmosphere": "air", "mechanism": "thermal_oxidation", "confidence": 0.82},
        ],
    },
    "FKM": {
        "type": "fluoropolymer",
        "full_name": "Fluoroelastomer",
        "common_names": ["Viton", "Fluorel"],
        "degradation_products": [
            {"child": "HF", "temp_range": "300-450°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.92},
        ],
    },
    # Legacy PFAS (Long-chain)
    "PFOA": {
        "type": "pfas_legacy",
        "full_name": "Perfluorooctanoic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "PFHpA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.70},
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.95},
            {"child": "HF", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.95},
        ],
    },
    "PFOS": {
        "type": "pfas_legacy",
        "full_name": "Perfluorooctanesulfonic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.92},
            {"child": "HF", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.92},
            {"child": "SO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.90},
        ],
    },
    "PFNA": {
        "type": "pfas_legacy",
        "full_name": "Perfluorononanoic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.90},
            {"child": "HF", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.90},
        ],
    },
    "PFDA": {
        "type": "pfas_legacy",
        "full_name": "Perfluorodecanoic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.88},
            {"child": "HF", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.88},
        ],
    },
    "PFUnDA": {
        "type": "pfas_legacy",
        "full_name": "Perfluoroundecanoic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
        ],
    },
    "PFDoDA": {
        "type": "pfas_legacy",
        "full_name": "Perfluorododecanoic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
        ],
    },
    # Short-chain PFAS
    "PFBA": {
        "type": "pfas_short_chain",
        "full_name": "Perfluorobutanoic acid",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">900°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
            {"child": "HF", "temp_range": ">900°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
        ],
    },
    "PFPeA": {
        "type": "pfas_short_chain",
        "full_name": "Perfluoropentanoic acid",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">900°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.82},
        ],
    },
    "PFHxA": {
        "type": "pfas_short_chain",
        "full_name": "Perfluorohexanoic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">900°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
            {"child": "HF", "temp_range": ">900°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
        ],
    },
    "PFHpA": {
        "type": "pfas_short_chain",
        "full_name": "Perfluoroheptanoic acid",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">900°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.82},
        ],
    },
    # Sulfonate PFAS
    "PFBS": {
        "type": "pfas_sulfonate",
        "full_name": "Perfluorobutanesulfonic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
            {"child": "HF", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
            {"child": "SO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.82},
        ],
    },
    "PFHxS": {
        "type": "pfas_sulfonate",
        "full_name": "Perfluorohexanesulfonic acid",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.88},
            {"child": "HF", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.88},
            {"child": "SO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.85},
        ],
    },
    # Ultra-short chain
    "TFA": {
        "type": "pfas_ultrashort",
        "full_name": "Trifluoroacetic acid",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "CO2", "temp_range": ">800°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.90},
            {"child": "HF", "temp_range": ">800°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.90},
        ],
    },
    # Replacement PFAS
    "GenX": {
        "type": "pfas_replacement",
        "full_name": "HFPO-DA (GenX)",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "TFA", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.78},
            {"child": "HF", "temp_range": "500-800°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.85},
            {"child": "CO2", "temp_range": ">1000°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.88},
        ],
    },
    "ADONA": {
        "type": "pfas_replacement",
        "full_name": "4,8-dioxa-3H-perfluorononanoic acid",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "TFA", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.72},
            {"child": "HF", "temp_range": "500-800°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.80},
        ],
    },
    "F-53B": {
        "type": "pfas_replacement",
        "full_name": "6:2 Chlorinated polyfluorinated ether sulfonate",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "PFHxS", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.65},
            {"child": "HF", "temp_range": ">800°C", "atmosphere": "air", "mechanism": "incineration", "confidence": 0.82},
        ],
    },
    # Fluorotelomers
    "6:2 FTS": {
        "type": "fluorotelomer",
        "full_name": "6:2 Fluorotelomer sulfonate",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "PFHxA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.85},
            {"child": "PFPeA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.75},
        ],
    },
    "8:2 FTS": {
        "type": "fluorotelomer",
        "full_name": "8:2 Fluorotelomer sulfonate",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "PFOA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.88},
            {"child": "PFHpA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.72},
        ],
    },
    "6:2 FTOH": {
        "type": "fluorotelomer",
        "full_name": "6:2 Fluorotelomer alcohol",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "PFHxA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.82},
            {"child": "5:3 FTCA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.70},
        ],
    },
    "8:2 FTOH": {
        "type": "fluorotelomer",
        "full_name": "8:2 Fluorotelomer alcohol",
        "is_pfas": True,
        "is_regulated": False,
        "degradation_products": [
            {"child": "PFOA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.85},
            {"child": "PFNA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.65},
        ],
    },
    # AFFF Components
    "AFFF-C6": {
        "type": "afff",
        "full_name": "C6 Fluorotelomer-based AFFF",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "PFHxA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.90},
            {"child": "6:2 FTS", "temp_range": "ambient", "atmosphere": "water", "mechanism": "hydrolysis", "confidence": 0.85},
        ],
    },
    "AFFF-C8": {
        "type": "afff",
        "full_name": "C8 Fluorotelomer-based AFFF (legacy)",
        "is_pfas": True,
        "is_regulated": True,
        "degradation_products": [
            {"child": "PFOA", "temp_range": "ambient", "atmosphere": "biological", "mechanism": "biotransformation", "confidence": 0.92},
            {"child": "PFOS", "temp_range": "ambient", "atmosphere": "water", "mechanism": "hydrolysis", "confidence": 0.88},
        ],
    },
    # Refrigerants (HFOs)
    "HFO-1234yf": {
        "type": "refrigerant",
        "full_name": "2,3,3,3-Tetrafluoropropene",
        "is_pfas": False,
        "is_regulated": False,
        "degradation_products": [
            {"child": "TFA", "temp_range": "ambient", "atmosphere": "air", "mechanism": "atmospheric_oxidation", "confidence": 0.95},
            {"child": "HF", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.88},
        ],
    },
    "HFO-1234ze": {
        "type": "refrigerant",
        "full_name": "trans-1,3,3,3-Tetrafluoropropene",
        "is_pfas": False,
        "is_regulated": False,
        "degradation_products": [
            {"child": "TFA", "temp_range": "ambient", "atmosphere": "air", "mechanism": "atmospheric_oxidation", "confidence": 0.92},
            {"child": "HF", "temp_range": "400-600°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.85},
        ],
    },
    "HFC-134a": {
        "type": "refrigerant",
        "full_name": "1,1,1,2-Tetrafluoroethane",
        "is_pfas": False,
        "is_regulated": True,
        "degradation_products": [
            {"child": "TFA", "temp_range": "ambient", "atmosphere": "air", "mechanism": "atmospheric_oxidation", "confidence": 0.88},
            {"child": "HF", "temp_range": "500-700°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.92},
        ],
    },
    # Fluorinated gases
    "SF6": {
        "type": "industrial_gas",
        "full_name": "Sulfur hexafluoride",
        "is_pfas": False,
        "is_regulated": True,
        "degradation_products": [
            {"child": "SO2", "temp_range": ">500°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.75},
            {"child": "HF", "temp_range": ">500°C", "atmosphere": "humid_air", "mechanism": "hydrolysis", "confidence": 0.70},
        ],
    },
    "NF3": {
        "type": "industrial_gas",
        "full_name": "Nitrogen trifluoride",
        "is_pfas": False,
        "is_regulated": True,
        "degradation_products": [
            {"child": "HF", "temp_range": ">400°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.85},
            {"child": "NOx", "temp_range": ">500°C", "atmosphere": "air", "mechanism": "thermal_decomposition", "confidence": 0.80},
        ],
    },
    # Intermediates/Products
    "HF": {
        "type": "degradation_product",
        "full_name": "Hydrogen fluoride",
        "is_pfas": False,
        "is_regulated": True,
        "is_endpoint": True,
        "degradation_products": [],
    },
    "COF2": {
        "type": "degradation_product",
        "full_name": "Carbonyl fluoride",
        "is_pfas": False,
        "is_regulated": True,
        "degradation_products": [
            {"child": "HF", "temp_range": "ambient", "atmosphere": "humid_air", "mechanism": "hydrolysis", "confidence": 0.95},
            {"child": "CO2", "temp_range": "ambient", "atmosphere": "humid_air", "mechanism": "hydrolysis", "confidence": 0.95},
        ],
    },
    "CF4": {
        "type": "degradation_product",
        "full_name": "Tetrafluoromethane",
        "is_pfas": False,
        "is_regulated": True,
        "is_endpoint": True,
        "degradation_products": [],
    },
    "C2F6": {
        "type": "degradation_product",
        "full_name": "Hexafluoroethane",
        "is_pfas": False,
        "is_regulated": True,
        "is_endpoint": True,
        "degradation_products": [],
    },
    "C3F8": {
        "type": "degradation_product",
        "full_name": "Octafluoropropane",
        "is_pfas": False,
        "is_regulated": True,
        "is_endpoint": True,
        "degradation_products": [],
    },
}


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


class FateQueryResponse(BaseModel):
    """Response for fate query."""
    query: str
    total_transformations: int
    transformations: List[Transformation]
    compounds_involved: List[str]


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
    """Get list of parent compounds that have degradation pathways."""
    database = get_pfas_database()

    # Get all compounds with degradation products (parents)
    parents = []
    for name, data in database.items():
        products = data.get("degradation_products", [])
        if products and not data.get("is_endpoint"):
            parents.append(name)

    # Sort by number of degradation products (most first), then alphabetically
    parents.sort(key=lambda n: (-len(database[n].get("degradation_products", [])), n))

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

    if parent_data:
        for product in parent_data.get("degradation_products", []):
            child = product["child"]
            compounds.add(child)

            # Parse temperature range
            product_temp_range = product.get("temp_range", "N/A")
            prod_min, prod_max = _parse_temp_range(product_temp_range)

            # Apply temperature filter
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
            ))

    # Also check graph for any additional pathways not in database
    graph = get_graph()
    if parent in graph or parent_upper in graph:
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
                source_count=len(data.get("evidence_refs", [])) or 1,
            ))

    # Sort by score descending
    transformations.sort(key=lambda t: t.score, reverse=True)

    return FateQueryResponse(
        query=f"{parent_upper} at {temp_min}-{temp_max}°C",
        total_transformations=len(transformations),
        transformations=transformations,
        compounds_involved=list(compounds),
    )
