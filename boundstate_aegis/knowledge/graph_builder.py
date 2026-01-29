#!/usr/bin/env python3
"""
Module: graph_builder
Purpose: PFAS knowledge graph construction and management using NetworkX.
    Provides PFASKnowledgeGraph class backed by MultiDiGraph for pathway
    storage, and build_graph() factory function to load from YAML sources.

    Rev History:
        1.0.0 - Initial graph builder with YAML pathway loading

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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import networkx as nx
except ModuleNotFoundError as _nx_exc:
    nx = None
    _NETWORKX_IMPORT_ERROR = _nx_exc
else:
    _NETWORKX_IMPORT_ERROR = None

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

from boundstate_aegis.models.pfas_compounds import CompoundNode, KNOWN_PFAS_ENDPOINTS
from boundstate_aegis.models.degradation_pathways import DegradationEdge
from boundstate_aegis.models.risk_models import EvidenceRow
from boundstate_aegis.config import DATA_DIR, PATHWAYS_DIR, CONFIDENCE_MAPPING

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
            logger.debug("Could not coerce value to float: %r", value)
            return None
    return None


def _normalize_confidence(conf: Any) -> float:
    """Normalize confidence values from various formats."""
    if conf is None:
        return 1.0
    if isinstance(conf, (int, float)):
        return float(conf)
    if isinstance(conf, str):
        lowered = conf.strip().lower()
        if lowered in CONFIDENCE_MAPPING:
            return CONFIDENCE_MAPPING[lowered]
        try:
            return float(lowered)
        except ValueError:
            return 1.0
    return 1.0


def _normalise_evidence(evidence: Any) -> List[EvidenceRow]:
    """
    Convert flexible evidence representations into EvidenceRow objects.

    Accepts Lists/Dicts/strings and coerces them into BoundState-compliant
    evidence records to satisfy SWE-013 and SWE-033 traceability requirements.
    """
    if not evidence:
        return []

    if isinstance(evidence, list) and all(isinstance(e, EvidenceRow) for e in evidence):
        return evidence

    normalised: List[EvidenceRow] = []
    source_items: Iterable[Any]

    if isinstance(evidence, dict):
        source_items = [evidence]
    elif isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        source_items = evidence
    else:
        source_items = [evidence]

    for item in source_items:
        if isinstance(item, EvidenceRow):
            normalised.append(item)
        elif isinstance(item, dict):
            normalised.append(
                EvidenceRow(
                    property=item.get("property", "pathway_citation"),
                    value=item.get("value", "cited"),
                    source=item.get("source", item.get("reference", "unknown")),
                    test_method=item.get("test_method", "literature_review"),
                    date=str(item.get("date", "1900-01-01")),
                    confidence=float(item.get("confidence", 1.0)),
                    notes=item.get("notes"),
                )
            )
        elif isinstance(item, str):
            normalised.append(
                EvidenceRow(
                    property="pathway_citation",
                    value="cited",
                    source=item,
                    test_method="literature_review",
                    date="1900-01-01",
                    confidence=0.5,
                )
            )

    return normalised


class PFASKnowledgeGraph:
    """
    MultiDiGraph-backed container for PFAS degradation pathways.

    Manages compound nodes and degradation edges, supporting pathway
    tracing and regulatory metadata queries.
    """

    def __init__(self) -> None:
        if nx is None:
            raise RuntimeError(
                "networkx is required for PFASKnowledgeGraph. "
                "Install it with `pip install networkx`."
            ) from _NETWORKX_IMPORT_ERROR
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self.compounds: Dict[str, CompoundNode] = {}

    def is_acyclic(self) -> bool:
        """Return True when the degradation graph behaves as a DAG."""
        return nx.algorithms.dag.is_directed_acyclic_graph(self.graph)

    def validate_graph(self) -> None:
        """Warn when cycles are detected."""
        if not self.is_acyclic():
            logger.warning(
                "PFASKnowledgeGraph.validate_graph: graph contains cycles; "
                "pathway tracing may not be reliable."
            )

    def add_compound(self, compound: CompoundNode) -> None:
        """Register or update a compound node with its associated metadata."""
        self.compounds[compound.name] = compound
        alias_pool = list(
            dict.fromkeys(
                [*(compound.aliases or []), *(compound.common_aliases or [])]
            )
        )
        node_attrs = {
            "is_pfas": compound.is_pfas,
            "is_short_chain_pfas": compound.is_short_chain_pfas,
            "cas_number": compound.cas_number,
            "aliases": alias_pool,
            "litigation_flag": compound.litigation_flag,
        }
        if compound.common_aliases:
            node_attrs["common_aliases"] = compound.common_aliases
        node_attrs.update(compound.metadata)
        self.graph.add_node(compound.name, **node_attrs)

    def add_degradation_pathway(self, edge: DegradationEdge) -> None:
        """
        Add or merge a degradation pathway edge.

        If an existing parent→child edge with the same mechanism is present,
        merge confidence, evidence, and temperature windows.
        """
        if edge.parent not in self.graph:
            self.add_compound(CompoundNode(name=edge.parent))
        if edge.child not in self.graph:
            self.add_compound(CompoundNode(name=edge.child))

        existing_edges = self.graph.get_edge_data(edge.parent, edge.child, default={})
        existing_key = None
        for key, data in existing_edges.items():
            if data.get("mechanism") == edge.mechanism:
                existing_key = key
                break

        if existing_key is not None:
            current = existing_edges[existing_key]
            cur_conf = _coerce_float(current.get("confidence")) or 1.0
            new_conf = _coerce_float(edge.confidence) or 1.0
            current["confidence"] = (cur_conf + new_conf) / 2.0

            current_refs = _normalise_evidence(current.get("evidence_refs"))
            new_refs = _normalise_evidence(edge.evidence_refs)
            dedup: Dict[Tuple[Any, ...], EvidenceRow] = {}
            for ref in [*current_refs, *new_refs]:
                key = (ref.property, ref.value, ref.source, ref.test_method, ref.date)
                dedup[key] = ref
            current["evidence_refs"] = list(dedup.values())

            def _merge_min(a: Any, b: Any) -> Optional[float]:
                va, vb = _coerce_float(a), _coerce_float(b)
                if va is None:
                    return vb
                if vb is None:
                    return va
                return min(va, vb)

            def _merge_max(a: Any, b: Any) -> Optional[float]:
                va, vb = _coerce_float(a), _coerce_float(b)
                if va is None:
                    return vb
                if vb is None:
                    return va
                return max(va, vb)

            current["min_temp_c"] = _merge_min(current.get("min_temp_c"), edge.min_temp_c)
            current["max_temp_c"] = _merge_max(current.get("max_temp_c"), edge.max_temp_c)
            current["atmosphere"] = current.get("atmosphere") or edge.atmosphere
            current["residence_time_s"] = current.get("residence_time_s") or edge.residence_time_s
            return

        self.graph.add_edge(
            edge.parent,
            edge.child,
            mechanism=edge.mechanism,
            min_temp_c=edge.min_temp_c,
            max_temp_c=edge.max_temp_c,
            atmosphere=edge.atmosphere,
            residence_time_s=edge.residence_time_s,
            confidence=edge.confidence,
            evidence_refs=_normalise_evidence(edge.evidence_refs),
        )

    def get_node_attributes(self, name: str) -> Dict[str, Any]:
        """Return node attribute dictionary for a registered compound."""
        if name in self.graph:
            return dict(self.graph.nodes[name])
        return {}

    def get_compound(self, name: str) -> Optional[CompoundNode]:
        """Get compound by name."""
        return self.compounds.get(name)

    def list_compounds(self) -> List[str]:
        """List all compound names in graph."""
        return list(self.compounds.keys())

    def list_pfas_compounds(self) -> List[str]:
        """List all compounds marked as PFAS."""
        return [
            name for name, compound in self.compounds.items()
            if compound.is_pfas
        ]


def _load_pathways_from_yaml(yaml_path: Path) -> List[Dict[str, Any]]:
    """Load pathway definitions from a YAML file."""
    if not yaml_path.exists() or yaml_path.stat().st_size == 0:
        return []
    if yaml is None:
        raise RuntimeError(
            f"PyYAML is required to load {yaml_path.name} but is not installed."
        )
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    pathways: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        # Check for nested structure: degradation_pathways: {parent: [...]}
        raw = data.get("pathways") or data.get("degradation_pathways") or data
        if isinstance(raw, dict):
            # Structure: {parent_compound: [pathway_entries...]}
            for parent_name, entries in raw.items():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict):
                            # Add parent/source to each entry
                            entry_copy = dict(entry)
                            entry_copy["source"] = parent_name
                            entry_copy["parent"] = parent_name
                            pathways.append(entry_copy)
        elif isinstance(raw, list):
            pathways = raw
    elif isinstance(data, list):
        pathways = data

    return pathways


def build_graph(
    pathway_list: Optional[List[Dict[str, Any]]] = None,
    load_from_data_dir: bool = True,
) -> PFASKnowledgeGraph:
    """
    Construct a knowledge graph populated with degradation pathways.

    Args:
        pathway_list: Optional list of pathway dictionaries to ingest.
        load_from_data_dir: When True, also load pathways from data/pathways/*.yaml

    Returns:
        Populated PFASKnowledgeGraph instance.
    """
    graph = PFASKnowledgeGraph()

    # Collect pathways from all sources
    all_pathways: List[Dict[str, Any]] = []

    if pathway_list is not None:
        all_pathways.extend(pathway_list)

    if load_from_data_dir:
        # Load from data/pathways/*.yaml
        if PATHWAYS_DIR.exists():
            for yaml_file in PATHWAYS_DIR.glob("*.yaml"):
                all_pathways.extend(_load_pathways_from_yaml(yaml_file))
            for yaml_file in PATHWAYS_DIR.glob("*.yml"):
                all_pathways.extend(_load_pathways_from_yaml(yaml_file))

        # Also check for legacy location
        legacy_path = DATA_DIR / "degradation_pathways.yaml"
        if legacy_path.exists():
            all_pathways.extend(_load_pathways_from_yaml(legacy_path))

    # Process pathways into edges
    for pathway in all_pathways:
        source_compound = (
            pathway.get("source")
            or pathway.get("parent")
            or pathway.get("compound")
            or pathway.get("material")
        )
        if not source_compound:
            continue

        conditions = pathway.get("conditions") or {}
        min_temp = _coerce_float(conditions.get("min_temp_c"))
        max_temp = _coerce_float(conditions.get("max_temp_c"))
        atmosphere = conditions.get("atmosphere")
        residence_time = _coerce_float(conditions.get("residence_time_s"))

        mechanism = pathway.get("mechanism") or pathway.get("mechanisms")
        if isinstance(mechanism, Sequence) and not isinstance(mechanism, str):
            mechanism = ", ".join(str(m) for m in mechanism)
        mechanism = mechanism or "thermal"

        confidence = _normalize_confidence(pathway.get("confidence"))
        evidence_refs = _normalise_evidence(pathway.get("evidence_refs"))

        products = pathway.get("products") or pathway.get("children") or []
        if isinstance(products, str):
            products = [products]

        for product in products:
            if not product:
                continue
            graph.add_degradation_pathway(
                DegradationEdge(
                    parent=str(source_compound),
                    child=str(product),
                    mechanism=str(mechanism),
                    min_temp_c=min_temp,
                    max_temp_c=max_temp,
                    atmosphere=atmosphere,
                    residence_time_s=residence_time,
                    confidence=confidence,
                    evidence_refs=evidence_refs,
                )
            )

    # Add known PFAS endpoints
    for node in KNOWN_PFAS_ENDPOINTS:
        graph.add_compound(node)

    return graph
