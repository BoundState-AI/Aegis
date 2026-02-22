#!/usr/bin/env python3
"""
Module: graph_queries
Purpose: Graph query utilities for pathway tracing and analysis.
    Provides trace_pathways() for degradation pathway discovery,
    get_downstream_products() and get_upstream_sources() for
    compound relationship analysis using NetworkX algorithms.

    Rev History:
        1.0.0 - Initial query functions with pathway tracing

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
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

try:
    import networkx as nx
except ModuleNotFoundError:
    nx = None

if TYPE_CHECKING:
    from boundstate_aegis.knowledge.graph_builder import PFASKnowledgeGraph

from boundstate_aegis.models.risk_models import EvidenceRow
from boundstate_aegis.config import DEFAULT_MAX_DEPTH, DEFAULT_MAX_RESULTS

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


def _normalise_evidence(evidence: Any) -> List[EvidenceRow]:
    """Convert evidence to EvidenceRow list."""
    if not evidence:
        return []
    if isinstance(evidence, list) and all(isinstance(e, EvidenceRow) for e in evidence):
        return evidence
    # Return empty if we can't process
    return []


def trace_pathways(
    graph: "PFASKnowledgeGraph",
    start_compound: str,
    targets: Optional[Iterable[str]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_results: Optional[int] = DEFAULT_MAX_RESULTS,
) -> List[Dict[str, Any]]:
    """
    Trace potential degradation pathways from a source compound to PFAS targets.

    Args:
        graph: PFASKnowledgeGraph instance to query
        start_compound: Source compound to trace from
        targets: Optional iterable of specific target compounds. Defaults to all PFAS nodes.
        max_depth: Maximum number of steps to explore
        max_results: Optional cap on number of paths returned

    Returns:
        List of pathway dictionaries with path, confidence, conditions, evidence
    """
    if nx is None:
        raise RuntimeError("networkx is required for pathway tracing")

    if start_compound not in graph.graph:
        logger.info(
            "Compound '%s' not found in knowledge graph; no pathways traced",
            start_compound,
        )
        return []

    if targets is None:
        targets = {
            node
            for node, data in graph.graph.nodes(data=True)
            if data.get("is_pfas")
        }

    target_set = {t for t in targets if t in graph.graph}
    if not target_set:
        return []

    found_paths: List[Dict[str, Any]] = []
    for target in target_set:
        for path in nx.all_simple_paths(
            graph.graph, start_compound, target, cutoff=max_depth
        ):
            found_paths.append(_build_path_payload(graph, path))
            if max_results is not None and len(found_paths) >= max_results:
                logger.warning(
                    "Reached max_results limit (%s); stopping pathway traversal",
                    max_results,
                )
                return found_paths

    return found_paths


def _build_path_payload(graph: "PFASKnowledgeGraph", path: Sequence[str]) -> Dict[str, Any]:
    """Build pathway payload dictionary from a path sequence."""
    path_conditions: List[Dict[str, Any]] = []
    aggregated_evidence_rows: Dict[Tuple[Any, ...], EvidenceRow] = {}
    cumulative_confidence = 1.0

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge_multidict = graph.graph.get_edge_data(u, v, default={})
        if not edge_multidict:
            continue

        parallels = list(edge_multidict.values())
        confidences: List[float] = []
        evidence_pool: List[EvidenceRow] = []
        base_record: Dict[str, Any] = {}

        for data in parallels:
            confidences.append(_coerce_float(data.get("confidence")) or 1.0)
            evidence_pool.extend(_normalise_evidence(data.get("evidence_refs")))
            if not base_record:
                base_record = dict(data)

        if confidences:
            cumulative_confidence *= sum(confidences) / len(confidences)

        for ref in evidence_pool:
            key = (ref.property, ref.value, ref.source, ref.test_method, ref.date)
            aggregated_evidence_rows.setdefault(key, ref)

        path_conditions.append({
            "step": f"{u} -> {v}",
            "mechanism": base_record.get("mechanism"),
            "min_temp_c": base_record.get("min_temp_c"),
            "max_temp_c": base_record.get("max_temp_c"),
            "atmosphere": base_record.get("atmosphere"),
            "residence_time_s": base_record.get("residence_time_s"),
        })

    return {
        "path": list(path),
        "confidence": cumulative_confidence,
        "conditions": path_conditions,
        "evidence_refs": [
            ref.to_dict() for ref in aggregated_evidence_rows.values()
        ],
    }


def get_downstream_products(
    graph: "PFASKnowledgeGraph",
    compound: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> List[str]:
    """
    Get all compounds reachable from a source compound.

    Args:
        graph: PFASKnowledgeGraph instance
        compound: Source compound name
        max_depth: Maximum path length to explore

    Returns:
        List of reachable compound names
    """
    if nx is None:
        raise RuntimeError("networkx is required")

    if compound not in graph.graph:
        return []

    # Single BFS traversal with cutoff avoids O(V^2)-style repeated path checks.
    path_lengths = nx.single_source_shortest_path_length(
        graph.graph, compound, cutoff=max_depth
    )
    return [node for node in path_lengths if node != compound]


def get_upstream_sources(
    graph: "PFASKnowledgeGraph",
    compound: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> List[str]:
    """
    Get all compounds that can degrade to a target compound.

    Args:
        graph: PFASKnowledgeGraph instance
        compound: Target compound name
        max_depth: Maximum path length to explore

    Returns:
        List of source compound names
    """
    if nx is None:
        raise RuntimeError("networkx is required")

    if compound not in graph.graph:
        return []

    # Use reverse graph to find upstream
    reverse_graph = graph.graph.reverse()
    path_lengths = nx.single_source_shortest_path_length(
        reverse_graph, compound, cutoff=max_depth
    )
    return [node for node in path_lengths if node != compound]
