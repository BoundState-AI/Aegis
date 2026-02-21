#!/usr/bin/env python3
"""
Recursive Regulatory Resolver (RRR).

Deterministic resolver for:
compound identity -> degradation tree -> governed assertion matching -> threat flags.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from boundstate_aegis.config import CLIENT_PROFILE, COMPOUNDS_DIR, PFAS_FATE_V2_JSON
from boundstate_aegis.engines.capability_registry import CapabilityRegistry
from boundstate_aegis.engines.product_manifest import ProductManifest
from boundstate_aegis.knowledge.graph_builder import get_cached_graph
from boundstate_aegis.monitoring.assertions import AssertionStore

try:
    from rdkit import Chem
except Exception:  # pragma: no cover - optional dependency fallback
    Chem = None


RESOLVER_VERSION = "1.0.0"

_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
_INCHIKEY_RE = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")

_REGISTRY_LOCK = threading.Lock()
_REGISTRY_CACHE: Optional[Dict[str, Any]] = None

_V2_LOCK = threading.Lock()
_V2_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None

_CACHE_LOCK = threading.Lock()
_RESOLUTION_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
_RESOLUTION_CACHE_MAX = 512


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_token(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_assertion_status(raw: str) -> str:
    token = (raw or "").strip().lower()
    if token in {"enforced", "adopted"}:
        return token
    if token in {"consultation", "proposed", "withdrawn"}:
        return token
    if token in {"finalized", "final", "effective"}:
        return "adopted"
    if token in {"pending", "draft", "monitoring"}:
        return "proposed"
    if not token:
        return "proposed"
    return "proposed"


def _severity_rank(level: str) -> int:
    order = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}
    return order.get((level or "INFO").upper(), 1)


def _derive_jurisdiction(assertion_id: str) -> str:
    prefix = (assertion_id or "").split("_", 1)[0].upper()
    mapping = {
        "US": "US",
        "EU": "EU",
        "CAN": "Canada",
        "JPN": "Japan",
        "KOR": "South Korea",
        "CHN": "China",
        "AUS": "Australia",
        "SGP": "Singapore",
        "TWN": "Taiwan",
        "IND": "India",
        "UK": "UK",
        "DNK": "Denmark",
        "NOR": "Norway",
        "DEU": "Germany",
        "SWE": "Sweden",
        "NLD": "Netherlands",
        "INTL": "International",
        "TFA": "International",
    }
    return mapping.get(prefix, prefix or "UNKNOWN")


@dataclass(frozen=True)
class CompoundIdentity:
    preferred_name: str
    cas: Optional[str] = None
    smiles: Optional[str] = None
    inchi_key: Optional[str] = None
    compound_classes: Tuple[str, ...] = ()
    pfas_class: bool = False
    synonyms: Tuple[str, ...] = ()
    resolution_method: str = "unresolved"
    product_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preferred_name": self.preferred_name,
            "cas": self.cas,
            "smiles": self.smiles,
            "inchi_key": self.inchi_key,
            "compound_classes": list(self.compound_classes),
            "pfas_class": self.pfas_class,
            "resolution_method": self.resolution_method,
            "product_info": self.product_info,
        }


@dataclass
class MatchedAssertion:
    assertion_id: str
    jurisdiction: str
    title: str
    status: str
    severity: str
    effective_date: Optional[str]
    source_url: Optional[str]
    confidence: float
    match_tier: str
    match_type: str
    matched_on: str
    inherited_from: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "jurisdiction": self.jurisdiction,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "effective_date": self.effective_date,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "match_tier": self.match_tier,
            "match_type": self.match_type,
            "matched_on": self.matched_on,
            "inherited_from": self.inherited_from,
        }


@dataclass
class DegradationNode:
    compound: CompoundIdentity
    depth: int
    pathway_from_parent: Dict[str, Any]
    edge_confidence: float
    cumulative_confidence: float
    citations: List[str]
    regulatory_exposure: List[MatchedAssertion] = field(default_factory=list)
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compound": self.compound.to_dict(),
            "depth": self.depth,
            "pathway_from_parent": self.pathway_from_parent,
            "edge_confidence": self.edge_confidence,
            "cumulative_confidence": self.cumulative_confidence,
            "citations": self.citations,
            "regulatory_exposure": [r.to_dict() for r in self.regulatory_exposure],
            "children": list(self.children),
        }


@dataclass
class DegradationTree:
    root: str
    nodes: List[DegradationNode]
    total_nodes: int
    max_depth_reached: int
    truncated: bool = False
    cycles_detected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root,
            "nodes": [n.to_dict() for n in self.nodes],
            "total_nodes": self.total_nodes,
            "max_depth_reached": self.max_depth_reached,
            "truncated": self.truncated,
            "cycles_detected": list(dict.fromkeys(self.cycles_detected)),
        }


@dataclass
class ExposureProfile:
    direct: List[MatchedAssertion]
    class_level: List[MatchedAssertion]
    inherited: List[MatchedAssertion]


@dataclass
class ThreatFlag:
    flag_type: str
    severity: str
    score: float
    compound: str
    detail: str
    citations: List[str]
    human_review_required: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flag_type": self.flag_type,
            "severity": self.severity,
            "score": self.score,
            "compound": self.compound,
            "detail": self.detail,
            "citations": self.citations,
            "human_review_required": self.human_review_required,
        }


class UnresolvableCompound(ValueError):
    pass


def _load_registry() -> Dict[str, Any]:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    with _REGISTRY_LOCK:
        if _REGISTRY_CACHE is not None:
            return _REGISTRY_CACHE
        path = COMPOUNDS_DIR / "compound_registry_clean.json"
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh) or {}
        compounds = raw.get("compounds", {}) if isinstance(raw, dict) else {}

        by_cas: Dict[str, Dict[str, Any]] = {}
        by_inchi: Dict[str, Dict[str, Any]] = {}
        by_name: Dict[str, Dict[str, Any]] = {}
        by_smiles: Dict[str, Dict[str, Any]] = {}
        for inchi, row in compounds.items():
            if not isinstance(row, dict):
                continue
            row_copy = dict(row)
            row_copy["inchi_key"] = inchi
            cas = str(row_copy.get("cas") or "").strip()
            if cas:
                by_cas[cas] = row_copy
            ik = str(row_copy.get("inchi_key") or "").strip().upper()
            if ik:
                by_inchi[ik] = row_copy
            smiles = str(row_copy.get("smiles_canonical") or row_copy.get("smiles_raw") or "").strip()
            if smiles:
                by_smiles[smiles] = row_copy
            names = [row_copy.get("primary_name")] + list(row_copy.get("aliases") or [])
            for name in names:
                if not name:
                    continue
                by_name[_normalize_token(str(name))] = row_copy

        _REGISTRY_CACHE = {
            "raw": raw,
            "by_cas": by_cas,
            "by_inchi": by_inchi,
            "by_name": by_name,
            "by_smiles": by_smiles,
        }
        return _REGISTRY_CACHE


def _load_v2_adjacency() -> Dict[str, List[Dict[str, Any]]]:
    global _V2_CACHE
    if _V2_CACHE is not None:
        return _V2_CACHE
    with _V2_LOCK:
        if _V2_CACHE is not None:
            return _V2_CACHE
        if not PFAS_FATE_V2_JSON.exists():
            _V2_CACHE = {}
            return _V2_CACHE
        with open(PFAS_FATE_V2_JSON, encoding="utf-8") as fh:
            raw = json.load(fh) or {}
        rows = raw.get("pathways") if isinstance(raw, dict) else []
        adjacency: Dict[str, List[Dict[str, Any]]] = {}
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                precursor = str(row.get("precursor") or "").strip()
                product = str(row.get("product") or "").strip()
                if not precursor or not product:
                    continue
                adjacency.setdefault(precursor, []).append(
                    {
                        "product": product,
                        "mechanism": str(row.get("mechanism") or "unknown"),
                        "confidence": float(row.get("evidence_score") or 0.5),
                        "citations": [str(x) for x in (row.get("source_dois") or []) if str(x).strip()],
                        "conditions": (
                            f"temp_bucket={row.get('temp_bucket')}, "
                            f"temp_c_median={row.get('temp_c_median')}, "
                            f"temp_c_range={row.get('temp_c_range')}"
                        ),
                    }
                )
        _V2_CACHE = adjacency
        return _V2_CACHE


def _identity_from_registry_row(row: Dict[str, Any], *, method: str, product_info: Optional[Dict[str, Any]] = None) -> CompoundIdentity:
    name = str(row.get("primary_name") or row.get("canonical_name") or row.get("name") or "").strip()
    classes: List[str] = []
    if row.get("type"):
        classes.append(str(row.get("type")))
    if row.get("class"):
        classes.append(str(row.get("class")))
    is_pfas = bool(row.get("is_pfas", False)) or "pf" in name.lower() or "fluoro" in name.lower()
    aliases = tuple(str(x).strip() for x in (row.get("aliases") or []) if str(x).strip())
    return CompoundIdentity(
        preferred_name=name or "unknown",
        cas=(str(row.get("cas")).strip() if row.get("cas") else None),
        smiles=(str(row.get("smiles_canonical") or row.get("smiles_raw")).strip() if (row.get("smiles_canonical") or row.get("smiles_raw")) else None),
        inchi_key=(str(row.get("inchi_key")).strip().upper() if row.get("inchi_key") else None),
        compound_classes=tuple(dict.fromkeys(classes)),
        pfas_class=is_pfas,
        synonyms=aliases,
        resolution_method=method,
        product_info=product_info,
    )


def _identity_from_graph_node(name: str, attrs: Dict[str, Any], *, method: str) -> CompoundIdentity:
    aliases = [*list(attrs.get("aliases") or []), *list(attrs.get("common_aliases") or [])]
    cas = attrs.get("cas_number")
    classes: List[str] = []
    if attrs.get("type"):
        classes.append(str(attrs.get("type")))
    if attrs.get("pfas_category"):
        classes.append(str(attrs.get("pfas_category")))
    pfas_class = bool(attrs.get("is_pfas")) or "pf" in name.lower() or "fluoro" in name.lower()
    return CompoundIdentity(
        preferred_name=name,
        cas=(str(cas).strip() if cas else None),
        smiles=None,
        inchi_key=None,
        compound_classes=tuple(dict.fromkeys(classes)),
        pfas_class=pfas_class,
        synonyms=tuple(str(x).strip() for x in aliases if str(x).strip()),
        resolution_method=method,
        product_info=None,
    )


def _identity_from_name(name: str, *, method: str = "normalized_name") -> CompoundIdentity:
    registry = _load_registry()
    norm = _normalize_token(name)
    row = registry["by_name"].get(norm)
    if row:
        return _identity_from_registry_row(row, method=method)
    return CompoundIdentity(
        preferred_name=name,
        cas=None,
        smiles=None,
        inchi_key=None,
        compound_classes=(),
        pfas_class=("pf" in name.lower() or "fluoro" in name.lower()),
        synonyms=(),
        resolution_method=method,
        product_info=None,
    )


def _looks_like_smiles(text: str) -> bool:
    token = (text or "").strip()
    if not token:
        return False
    if " " in token:
        return False
    # Basic heuristic: common atom/bond syntax markers.
    return bool(re.search(r"[=#\[\]\(\)\\/]|[BCNOFPSIclbr]", token))


def resolve_compound(
    input_str: str,
    manifest: ProductManifest,
    graph: Optional[Any] = None,
) -> CompoundIdentity:
    token = (input_str or "").strip()
    if not token:
        raise UnresolvableCompound("Compound input is empty")

    registry = _load_registry()
    graph_obj = graph or get_cached_graph()
    graph_nodes = graph_obj.graph.nodes if hasattr(graph_obj, "graph") else {}

    product_hit = manifest.lookup_product(token)
    if product_hit:
        if product_hit.cas and product_hit.cas in registry["by_cas"]:
            return _identity_from_registry_row(
                registry["by_cas"][product_hit.cas],
                method="product_manifest",
                product_info=product_hit.to_product_info(),
            )
        if product_hit.components:
            for component in product_hit.components:
                cas = str(component.get("cas") or "").strip()
                if cas and cas in registry["by_cas"]:
                    return _identity_from_registry_row(
                        registry["by_cas"][cas],
                        method="product_manifest",
                        product_info=product_hit.to_product_info(),
                    )
        return CompoundIdentity(
            preferred_name=product_hit.product_name,
            cas=product_hit.cas,
            smiles=product_hit.smiles,
            inchi_key=product_hit.inchi_key,
            compound_classes=product_hit.compound_classes,
            pfas_class=product_hit.pfas_class,
            synonyms=product_hit.aliases,
            resolution_method="product_manifest",
            product_info=product_hit.to_product_info(),
        )

    if _CAS_RE.match(token) and token in registry["by_cas"]:
        return _identity_from_registry_row(registry["by_cas"][token], method="exact_cas")

    upper_token = token.upper()
    if _INCHIKEY_RE.match(upper_token) and upper_token in registry["by_inchi"]:
        return _identity_from_registry_row(registry["by_inchi"][upper_token], method="exact_inchikey")

    if _looks_like_smiles(token):
        if token in registry["by_smiles"]:
            return _identity_from_registry_row(registry["by_smiles"][token], method="smiles_resolution")
        if Chem is not None:
            mol = Chem.MolFromSmiles(token)
            if mol is not None:
                canonical = Chem.MolToSmiles(mol, canonical=True)
                if canonical in registry["by_smiles"]:
                    return _identity_from_registry_row(
                        registry["by_smiles"][canonical],
                        method="smiles_resolution",
                    )

    norm = _normalize_token(token)
    if norm in registry["by_name"]:
        return _identity_from_registry_row(registry["by_name"][norm], method="normalized_name")

    # Exact match against graph node names and aliases.
    for node_name, attrs in graph_nodes.items():
        if _normalize_token(str(node_name)) == norm:
            return _identity_from_graph_node(str(node_name), dict(attrs), method="normalized_name")
        aliases = list(attrs.get("aliases") or []) + list(attrs.get("common_aliases") or [])
        for alias in aliases:
            if _normalize_token(str(alias)) == norm:
                return _identity_from_graph_node(str(node_name), dict(attrs), method="normalized_name")

    # Fuzzy fallback against graph nodes.
    best_name: Optional[str] = None
    best_attrs: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for node_name, attrs in graph_nodes.items():
        score = SequenceMatcher(None, norm, _normalize_token(str(node_name))).ratio()
        if score > best_score:
            best_name = str(node_name)
            best_attrs = dict(attrs)
            best_score = score
    if best_name and best_attrs and best_score >= 0.85:
        return _identity_from_graph_node(best_name, best_attrs, method="fuzzy_name")

    raise UnresolvableCompound(f"Unable to resolve compound input '{input_str}'")


def _extract_citations_from_edge(edge_data: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    refs = edge_data.get("evidence_refs") or []
    for ref in refs:
        if isinstance(ref, dict):
            doi = ref.get("doi")
            source = ref.get("source")
            if doi:
                out.append(str(doi))
            elif source:
                out.append(str(source))
        elif hasattr(ref, "source"):
            source = getattr(ref, "source", None)
            if source:
                out.append(str(source))
    return list(dict.fromkeys(out))


def _edge_conditions(edge_data: Dict[str, Any]) -> str:
    fields: List[str] = []
    for key in ("min_temp_c", "max_temp_c", "atmosphere", "residence_time_s"):
        value = edge_data.get(key)
        if value is not None:
            fields.append(f"{key}={value}")
    return ", ".join(fields)


def _find_graph_node_name(identity: CompoundIdentity, graph_obj: Any) -> Optional[str]:
    g = graph_obj.graph
    if identity.preferred_name in g:
        return identity.preferred_name

    search_tokens = [identity.preferred_name, *list(identity.synonyms)]
    normalized_targets = [_normalize_token(x) for x in search_tokens if _normalize_token(x)]
    for norm_target in normalized_targets:
        for node_name, attrs in g.nodes(data=True):
            if _normalize_token(str(node_name)) == norm_target:
                return str(node_name)
            cas = str(attrs.get("cas_number") or "").strip()
            if identity.cas and cas and identity.cas == cas:
                return str(node_name)
            aliases = list(attrs.get("aliases") or []) + list(attrs.get("common_aliases") or [])
            for alias in aliases:
                if _normalize_token(str(alias)) == norm_target:
                    return str(node_name)

    best = None
    best_score = 0.0
    for norm_target in normalized_targets or [_normalize_token(identity.preferred_name)]:
        for node_name in g.nodes():
            score = SequenceMatcher(None, norm_target, _normalize_token(str(node_name))).ratio()
            if score > best_score:
                best = str(node_name)
                best_score = score
    if best and best_score >= 0.85:
        return best
    return None


def _find_v2_root_name(identity: CompoundIdentity) -> Optional[str]:
    adjacency = _load_v2_adjacency()
    if not adjacency:
        return None
    candidates = [identity.preferred_name, *list(identity.synonyms)]
    keys = list(adjacency.keys())
    normalized = {_normalize_token(x): x for x in keys}
    for token in candidates:
        norm = _normalize_token(token)
        if norm in normalized:
            return normalized[norm]
    best = None
    best_score = 0.0
    for token in candidates:
        norm = _normalize_token(token)
        for precursor in keys:
            score = SequenceMatcher(None, norm, _normalize_token(precursor)).ratio()
            if score > best_score:
                best_score = score
                best = precursor
    if best and best_score >= 0.85:
        return best
    return None


def _build_tree_from_v2(
    compound: CompoundIdentity,
    *,
    max_depth: int,
    max_nodes: int,
    max_branching: int,
    min_confidence: float,
) -> Optional[DegradationTree]:
    adjacency = _load_v2_adjacency()
    if not adjacency:
        return None
    root_name = _find_v2_root_name(compound)
    if not root_name:
        return None

    # Ensure root identity reflects canonical precursor label in this dataset.
    root_identity = _identity_from_name(root_name, method=compound.resolution_method)
    if compound.product_info:
        root_identity = CompoundIdentity(
            preferred_name=root_identity.preferred_name,
            cas=root_identity.cas,
            smiles=root_identity.smiles,
            inchi_key=root_identity.inchi_key,
            compound_classes=root_identity.compound_classes,
            pfas_class=root_identity.pfas_class,
            synonyms=root_identity.synonyms,
            resolution_method=compound.resolution_method,
            product_info=compound.product_info,
        )

    nodes: Dict[str, DegradationNode] = {
        root_name: DegradationNode(
            compound=root_identity,
            depth=0,
            pathway_from_parent={"mechanism": "unknown", "conditions": "", "parent_compound": ""},
            edge_confidence=1.0,
            cumulative_confidence=1.0,
            citations=[],
        )
    }
    queue: List[Tuple[str, int, Tuple[str, ...], float]] = [(root_name, 0, (root_name,), 1.0)]
    visited = {root_name}
    truncated = False
    cycles_detected: List[str] = []
    max_depth_reached = 0

    while queue:
        current, depth, path, cumulative_parent = queue.pop(0)
        max_depth_reached = max(max_depth_reached, depth)
        if depth >= max_depth:
            continue

        children = []
        for edge in adjacency.get(current, []):
            conf = float(edge.get("confidence") or 0.0)
            if conf < min_confidence:
                continue
            children.append(edge)
        children.sort(key=lambda x: (-float(x.get("confidence") or 0.0), str(x.get("product") or "").lower()))
        if len(children) > max_branching:
            children = children[:max_branching]
            truncated = True

        parent_node = nodes[current]
        for edge in children:
            child_name = str(edge.get("product") or "").strip()
            if not child_name:
                continue
            if child_name in path:
                cycles_detected.append(child_name)
                continue
            parent_node.children.append(child_name)

            if child_name not in nodes:
                if len(nodes) >= max_nodes:
                    truncated = True
                    continue
                edge_conf = float(edge.get("confidence") or 0.0)
                child_identity = _identity_from_name(child_name, method="normalized_name")
                nodes[child_name] = DegradationNode(
                    compound=child_identity,
                    depth=depth + 1,
                    pathway_from_parent={
                        "mechanism": str(edge.get("mechanism") or "unknown"),
                        "conditions": str(edge.get("conditions") or ""),
                        "parent_compound": current,
                    },
                    edge_confidence=edge_conf,
                    cumulative_confidence=min(cumulative_parent, edge_conf),
                    citations=list(edge.get("citations") or []),
                )
            if child_name not in visited:
                visited.add(child_name)
                queue.append(
                    (
                        child_name,
                        depth + 1,
                        (*path, child_name),
                        min(cumulative_parent, float(edge.get("confidence") or 0.0)),
                    )
                )

    sorted_nodes = sorted(nodes.items(), key=lambda item: (item[1].depth, item[0].lower()))
    return DegradationTree(
        root=root_name,
        nodes=[node for _, node in sorted_nodes],
        total_nodes=len(sorted_nodes),
        max_depth_reached=max_depth_reached,
        truncated=truncated,
        cycles_detected=cycles_detected,
    )


def build_degradation_tree(
    compound: CompoundIdentity,
    graph_obj: Any,
    max_depth: int = 4,
    max_nodes: int = 50,
    max_branching: int = 10,
    min_confidence: float = 0.3,
) -> DegradationTree:
    g = graph_obj.graph
    root_name = _find_graph_node_name(compound, graph_obj) or compound.preferred_name

    if root_name not in g:
        fallback = _build_tree_from_v2(
            compound,
            max_depth=max_depth,
            max_nodes=max_nodes,
            max_branching=max_branching,
            min_confidence=min_confidence,
        )
        if fallback is not None:
            return fallback

    root_node = DegradationNode(
        compound=compound,
        depth=0,
        pathway_from_parent={"mechanism": "unknown", "conditions": "", "parent_compound": ""},
        edge_confidence=1.0,
        cumulative_confidence=1.0,
        citations=[],
    )
    nodes: Dict[str, DegradationNode] = {root_name: root_node}
    truncated = False
    cycles_detected: List[str] = []
    max_depth_reached = 0

    queue: List[Tuple[str, int, Tuple[str, ...], float]] = [(root_name, 0, (root_name,), 1.0)]
    visited = {root_name}

    while queue:
        current, depth, path, cumulative_parent = queue.pop(0)
        max_depth_reached = max(max_depth_reached, depth)
        if depth >= max_depth:
            continue
        if current not in g:
            continue

        child_edges: Dict[str, Dict[str, Any]] = {}
        for _, child, _key, edge_data in g.out_edges(current, keys=True, data=True):
            edge_conf = float(edge_data.get("confidence") or 1.0)
            if edge_conf < float(min_confidence):
                continue
            child_name = str(child)
            best = child_edges.get(child_name)
            if best is None or edge_conf > float(best["confidence"]):
                child_edges[child_name] = {
                    "confidence": edge_conf,
                    "mechanism": str(edge_data.get("mechanism") or "unknown"),
                    "conditions": _edge_conditions(edge_data),
                    "citations": _extract_citations_from_edge(edge_data),
                }

        ordered_children = sorted(child_edges.items(), key=lambda item: (-float(item[1]["confidence"]), item[0].lower()))
        if len(ordered_children) > max_branching:
            truncated = True
            ordered_children = ordered_children[:max_branching]

        parent_node = nodes[current]
        for child_name, detail in ordered_children:
            if child_name in path:
                cycles_detected.append(child_name)
                continue

            parent_node.children.append(child_name)
            if child_name not in nodes:
                if len(nodes) >= max_nodes:
                    truncated = True
                    continue
                child_attrs = dict(g.nodes[child_name]) if child_name in g else {}
                child_identity = _identity_from_graph_node(
                    child_name,
                    child_attrs,
                    method="normalized_name",
                )
                cumulative = min(cumulative_parent, float(detail["confidence"]))
                child_node = DegradationNode(
                    compound=child_identity,
                    depth=depth + 1,
                    pathway_from_parent={
                        "mechanism": detail["mechanism"],
                        "conditions": detail["conditions"],
                        "parent_compound": current,
                    },
                    edge_confidence=float(detail["confidence"]),
                    cumulative_confidence=float(cumulative),
                    citations=list(detail["citations"]),
                )
                nodes[child_name] = child_node
            if child_name not in visited:
                visited.add(child_name)
                queue.append(
                    (
                        child_name,
                        depth + 1,
                        (*path, child_name),
                        min(cumulative_parent, float(detail["confidence"])),
                    )
                )

    sorted_nodes = sorted(nodes.items(), key=lambda item: (item[1].depth, item[0].lower()))
    tree = DegradationTree(
        root=root_name,
        nodes=[node for _, node in sorted_nodes],
        total_nodes=len(sorted_nodes),
        max_depth_reached=max_depth_reached,
        truncated=truncated,
        cycles_detected=cycles_detected,
    )
    if tree.total_nodes <= 1:
        fallback = _build_tree_from_v2(
            compound,
            max_depth=max_depth,
            max_nodes=max_nodes,
            max_branching=max_branching,
            min_confidence=min_confidence,
        )
        if fallback is not None:
            return fallback
    return tree


def _assertion_to_match(
    assertion: Dict[str, Any],
    *,
    match_tier: str,
    match_type: str,
    matched_on: str,
    inherited_from: Optional[str],
    confidence_multiplier: float,
) -> MatchedAssertion:
    assertion_id = str(assertion.get("id") or "")
    dates = assertion.get("dates") or {}
    if not isinstance(dates, dict):
        dates = {}
    citations = assertion.get("citations") or []
    source_url: Optional[str] = None
    if isinstance(citations, list):
        for c in citations:
            if isinstance(c, dict) and c.get("url"):
                source_url = str(c.get("url"))
                break

    confidence = float(assertion.get("confidence") or 0.0)
    confidence = max(0.0, min(1.0, confidence * confidence_multiplier))

    raw_status = _normalize_assertion_status(str(assertion.get("status") or ""))
    litigation = str(assertion.get("litigation_relevance") or "").lower()
    if litigation == "critical":
        severity = "CRITICAL"
    elif litigation == "high":
        severity = "HIGH"
    elif confidence >= 0.95:
        severity = "HIGH"
    elif confidence >= 0.85:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    if raw_status in {"proposed", "consultation"} and severity == "LOW":
        severity = "MEDIUM"

    return MatchedAssertion(
        assertion_id=assertion_id,
        jurisdiction=_derive_jurisdiction(assertion_id),
        title=str(assertion.get("assertion") or ""),
        status=raw_status,
        severity=severity,
        effective_date=(dates.get("effective") or dates.get("finalized")),
        source_url=source_url,
        confidence=confidence,
        match_tier=match_tier,
        match_type=match_type,
        matched_on=matched_on,
        inherited_from=inherited_from,
    )


def _dedupe_matches(matches: Iterable[MatchedAssertion]) -> List[MatchedAssertion]:
    tier_rank = {
        "exact_cas": 5,
        "exact_inchikey": 4,
        "normalized_name": 3,
        "compound_class": 2,
        "pfas_class": 1,
    }
    best: Dict[Tuple[str, str], MatchedAssertion] = {}
    for row in matches:
        key = (row.assertion_id, row.match_type)
        current = best.get(key)
        if current is None:
            best[key] = row
            continue
        if tier_rank.get(row.match_tier, 0) > tier_rank.get(current.match_tier, 0):
            best[key] = row
    return sorted(best.values(), key=lambda x: (x.assertion_id, x.match_type))


def _match_assertions_for_compound(
    *,
    compound: CompoundIdentity,
    store: AssertionStore,
    match_type: str,
    inherited_from: Optional[str] = None,
    include_identity: bool = True,
    include_class: bool = True,
) -> List[MatchedAssertion]:
    rows: List[MatchedAssertion] = []

    if include_identity and compound.cas:
        for assertion in store.query_by_cas(compound.cas):
            rows.append(
                _assertion_to_match(
                    assertion,
                    match_tier="exact_cas",
                    match_type=match_type,
                    matched_on=f"CAS:{compound.cas}",
                    inherited_from=inherited_from,
                    confidence_multiplier=1.0,
                )
            )
    if include_identity and compound.inchi_key:
        for assertion in store.query_by_inchikey(compound.inchi_key):
            rows.append(
                _assertion_to_match(
                    assertion,
                    match_tier="exact_inchikey",
                    match_type=match_type,
                    matched_on=f"InChIKey:{compound.inchi_key}",
                    inherited_from=inherited_from,
                    confidence_multiplier=1.0,
                )
            )

    if include_identity:
        names = [compound.preferred_name, *list(compound.synonyms)]
        seen = set()
        for name in names:
            norm = _normalize_token(name)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            for assertion in store.query_by_name(name):
                rows.append(
                    _assertion_to_match(
                        assertion,
                        match_tier="normalized_name",
                        match_type=match_type,
                        matched_on=f"name:{name}",
                        inherited_from=inherited_from,
                        confidence_multiplier=0.95,
                    )
                )

    if include_class:
        for cls in compound.compound_classes:
            for assertion in store.query_by_compound_class(cls):
                rows.append(
                    _assertion_to_match(
                        assertion,
                        match_tier="compound_class",
                        match_type=match_type,
                        matched_on=f"class:{cls}",
                        inherited_from=inherited_from,
                        confidence_multiplier=0.8,
                    )
                )
        if compound.pfas_class:
            for assertion in store.query_universal_pfas():
                rows.append(
                    _assertion_to_match(
                        assertion,
                        match_tier="pfas_class",
                        match_type=match_type,
                        matched_on="pfas_class:true",
                        inherited_from=inherited_from,
                        confidence_multiplier=0.7,
                    )
                )

    return _dedupe_matches(rows)


def resolve_regulatory_exposure(
    tree: DegradationTree,
    query_compound: CompoundIdentity,
    assertion_store: AssertionStore,
) -> ExposureProfile:
    direct = _match_assertions_for_compound(
        compound=query_compound,
        store=assertion_store,
        match_type="direct",
        include_identity=True,
        include_class=False,
    )
    class_level = _match_assertions_for_compound(
        compound=query_compound,
        store=assertion_store,
        match_type="class",
        include_identity=False,
        include_class=True,
    )

    inherited_rows: List[MatchedAssertion] = []
    for node in tree.nodes:
        if node.depth == 0:
            node.regulatory_exposure = sorted(
                [*direct, *class_level],
                key=lambda x: (_severity_rank(x.severity), x.assertion_id),
                reverse=True,
            )
            continue
        node_matches = _match_assertions_for_compound(
            compound=node.compound,
            store=assertion_store,
            match_type="inherited",
            inherited_from=node.compound.preferred_name,
            include_identity=True,
            include_class=True,
        )
        node.regulatory_exposure = sorted(
            node_matches,
            key=lambda x: (_severity_rank(x.severity), x.assertion_id),
            reverse=True,
        )
        inherited_rows.extend(node_matches)

    inherited = _dedupe_matches(inherited_rows)
    return ExposureProfile(direct=direct, class_level=class_level, inherited=inherited)


def _score_inherited_liability(profile: ExposureProfile, root_compound: str) -> Optional[ThreatFlag]:
    parent_direct_count = len(profile.direct)
    child_assertion_count = len(profile.inherited)
    if child_assertion_count <= 0:
        return None

    child_max = "LOW"
    for row in profile.inherited:
        if _severity_rank(row.severity) > _severity_rank(child_max):
            child_max = row.severity

    delta = max(0, child_assertion_count - parent_direct_count)
    normalized_delta = delta / max(child_assertion_count, 1)
    severity_weight = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.2, "INFO": 0.1}
    score = max(0.0, min(1.0, normalized_delta * severity_weight.get(child_max, 0.2)))
    if score < 0.2:
        return None
    if score >= 0.7:
        severity = "CRITICAL"
        review = True
    elif score >= 0.4:
        severity = "HIGH"
        review = True
    else:
        severity = "MEDIUM"
        review = False

    citations = [x.source_url for x in profile.inherited if x.source_url][:5]
    return ThreatFlag(
        flag_type="INHERITED_LIABILITY",
        severity=severity,
        score=round(score, 4),
        compound=root_compound,
        detail=(
            f"Direct assertions={parent_direct_count}, inherited assertions={child_assertion_count}. "
            f"Regulatory burden is heavier on degradation products."
        ),
        citations=[c for c in citations if c],
        human_review_required=review,
    )


def _score_destruction_tech_gap(
    tree: DegradationTree,
    profile: ExposureProfile,
    capability_registry: CapabilityRegistry,
    client_name: str = "chemours",
) -> Optional[ThreatFlag]:
    best_score = 0.0
    best_node: Optional[DegradationNode] = None
    best_detail = ""
    best_citations: List[str] = []

    for node in tree.nodes:
        if node.depth == 0:
            continue
        assertion_count = len(node.regulatory_exposure)
        if assertion_count <= 0:
            continue
        compound_name = node.compound.preferred_name
        if capability_registry.has_client_capability(compound_name, client=client_name):
            continue
        available = capability_registry.get_available_technologies(compound_name)
        # If technology exists but is not owned/licensed by client, keep it below
        # "no technology exists" but still allow CRITICAL escalation for highly
        # regulated compounds.
        base = 1.0 if not available else 0.8
        score = min(1.0, base * min(1.0, assertion_count / 5.0))
        if score > best_score:
            best_score = score
            best_node = node
            best_detail = capability_registry.get_gap_detail(compound_name, client=client_name)
            best_citations = [x.source_url for x in node.regulatory_exposure if x.source_url][:5]

    if best_node is None or best_score < 0.2:
        return None

    if best_score >= 0.7 and len(best_node.regulatory_exposure) >= 3:
        severity = "CRITICAL"
    elif best_score >= 0.4:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    return ThreatFlag(
        flag_type="DESTRUCTION_TECH_GAP",
        severity=severity,
        score=round(best_score, 4),
        compound=best_node.compound.preferred_name,
        detail=best_detail,
        citations=[c for c in best_citations if c],
        human_review_required=True,
    )


def _score_regulatory_acceleration(assertions: Sequence[MatchedAssertion], root_compound: str) -> Optional[ThreatFlag]:
    if not assertions:
        return None
    proposed_count = len([a for a in assertions if a.status in {"proposed", "consultation"}])
    enforced_count = len([a for a in assertions if a.status in {"enforced", "adopted"}])
    jurisdiction_count = len({a.jurisdiction for a in assertions})
    score = (proposed_count / max(proposed_count + enforced_count, 1)) * (jurisdiction_count / 10.0)
    score = min(1.0, max(0.0, score))

    if jurisdiction_count >= 5 and proposed_count >= 3:
        severity = "CRITICAL"
        trajectory = "CONVERGING"
        review = True
    elif jurisdiction_count >= 3 and proposed_count >= 2:
        severity = "HIGH"
        trajectory = "ACCELERATING"
        review = True
    elif proposed_count >= 1 and score >= 0.2:
        severity = "MEDIUM"
        trajectory = "INCREASING"
        review = False
    else:
        return None

    citations = [a.source_url for a in assertions if a.source_url][:5]
    return ThreatFlag(
        flag_type="REGULATORY_ACCELERATION",
        severity=severity,
        score=round(score, 4),
        compound=root_compound,
        detail=(
            f"Trajectory {trajectory}: proposed={proposed_count}, enforced={enforced_count}, "
            f"jurisdictions={jurisdiction_count}."
        ),
        citations=[c for c in citations if c],
        human_review_required=review,
    )


def flag_threats(
    profile: ExposureProfile,
    tree: DegradationTree,
    capability_registry: CapabilityRegistry,
    client_profile: Dict[str, Any],
) -> List[ThreatFlag]:
    company = (
        (client_profile.get("chemours_exposure_profile") or {}).get("company")
        if isinstance(client_profile, dict)
        else None
    )
    client_key = "chemours" if company else "chemours"
    root_name = tree.nodes[0].compound.preferred_name if tree.nodes else tree.root

    flags: List[ThreatFlag] = []
    inherited_flag = _score_inherited_liability(profile, root_name)
    if inherited_flag:
        flags.append(inherited_flag)

    gap_flag = _score_destruction_tech_gap(tree, profile, capability_registry, client_name=client_key)
    if gap_flag:
        flags.append(gap_flag)

    accel_flag = _score_regulatory_acceleration(
        [*profile.direct, *profile.class_level, *profile.inherited],
        root_name,
    )
    if accel_flag:
        flags.append(accel_flag)

    return sorted(flags, key=lambda x: (_severity_rank(x.severity), x.score), reverse=True)


def _compute_total_exposure(profile: ExposureProfile, flags: Sequence[ThreatFlag]) -> Dict[str, Any]:
    all_rows = [*profile.direct, *profile.class_level, *profile.inherited]
    unique_assertions = {row.assertion_id: row for row in all_rows}
    jurisdictions = {row.jurisdiction for row in all_rows}

    if unique_assertions:
        most_severe = sorted(
            unique_assertions.values(),
            key=lambda row: (_severity_rank(row.severity), row.confidence),
            reverse=True,
        )[0]
        most_severe_id = most_severe.assertion_id
    else:
        most_severe_id = ""

    # Trajectory based on assertions; if acceleration flag exists, mirror it.
    trajectory = "STABLE"
    accel = next((f for f in flags if f.flag_type == "REGULATORY_ACCELERATION"), None)
    if accel:
        if accel.severity == "CRITICAL":
            trajectory = "CONVERGING"
        elif accel.severity == "HIGH":
            trajectory = "ACCELERATING"
        else:
            trajectory = "INCREASING"

    return {
        "jurisdictions_affected": len(jurisdictions),
        "assertions_triggered": len(unique_assertions),
        "most_severe_id": most_severe_id,
        "trajectory": trajectory,
    }


def _load_client_profile() -> Dict[str, Any]:
    path = Path(CLIENT_PROFILE)
    if not path.exists():
        return {}
    try:
        import yaml

        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _graph_version_hash() -> str:
    if not PFAS_FATE_V2_JSON.exists():
        return "missing_graph"
    data = PFAS_FATE_V2_JSON.read_bytes()
    return sha256(data).hexdigest()


def _cache_key(
    *,
    query: str,
    graph_version: str,
    assertion_version: str,
    manifest_version: str,
    max_depth: int,
    max_nodes: int,
    max_branching: int,
    min_confidence: float,
) -> Tuple[Any, ...]:
    return (
        query.strip().lower(),
        graph_version,
        assertion_version,
        manifest_version,
        int(max_depth),
        int(max_nodes),
        int(max_branching),
        round(float(min_confidence), 4),
    )


def resolve(
    input_str: str,
    max_depth: int = 4,
    max_nodes: int = 50,
    max_branching: int = 10,
    min_confidence: float = 0.3,
    include_evidence: bool = True,
) -> Dict[str, Any]:
    start = time.monotonic()

    graph_obj = get_cached_graph()
    manifest = ProductManifest.load()
    assertion_store = AssertionStore()
    assertion_store.ensure_bootstrapped()
    capability_registry = CapabilityRegistry.load()
    client_profile = _load_client_profile()

    graph_version = _graph_version_hash()
    assertion_version = assertion_store.assertion_version()
    manifest_version = manifest.version

    key = _cache_key(
        query=input_str,
        graph_version=graph_version,
        assertion_version=assertion_version,
        manifest_version=manifest_version,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_branching=max_branching,
        min_confidence=min_confidence,
    )
    with _CACHE_LOCK:
        cached = _RESOLUTION_CACHE.get(key)
    if cached is not None:
        # Return a deep copy to prevent caller mutation of cached state.
        return json.loads(json.dumps(cached))

    compound = resolve_compound(input_str, manifest=manifest, graph=graph_obj)
    tree = build_degradation_tree(
        compound=compound,
        graph_obj=graph_obj,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_branching=max_branching,
        min_confidence=min_confidence,
    )
    profile = resolve_regulatory_exposure(tree=tree, query_compound=compound, assertion_store=assertion_store)
    flags = flag_threats(profile=profile, tree=tree, capability_registry=capability_registry, client_profile=client_profile)

    duration_ms = int((time.monotonic() - start) * 1000)
    result = {
        "query_compound": compound.to_dict(),
        "direct_exposure": [x.to_dict() for x in profile.direct],
        "class_exposure": [x.to_dict() for x in profile.class_level],
        "degradation_tree": tree.to_dict(),
        "inherited_exposure": [x.to_dict() for x in profile.inherited],
        "total_exposure": _compute_total_exposure(profile, flags),
        "threat_flags": [x.to_dict() for x in flags],
        "metadata": {
            "resolver_version": RESOLVER_VERSION,
            "graph_version": graph_version,
            "assertion_version": assertion_version,
            "manifest_version": manifest_version,
            "resolved_at": _utc_now_iso(),
            "resolve_duration_ms": duration_ms,
            "traversal_params": {
                "max_depth": max_depth,
                "max_nodes": max_nodes,
                "max_branching": max_branching,
                "min_confidence": min_confidence,
            },
        },
    }
    if not include_evidence:
        for node in result["degradation_tree"]["nodes"]:
            node["citations"] = []
            for exp in node["regulatory_exposure"]:
                exp["source_url"] = None
        for group in ("direct_exposure", "class_exposure", "inherited_exposure"):
            for exp in result[group]:
                exp["source_url"] = None
        for flag in result["threat_flags"]:
            flag["citations"] = []

    with _CACHE_LOCK:
        if len(_RESOLUTION_CACHE) >= _RESOLUTION_CACHE_MAX:
            # Drop oldest arbitrary item (dict insertion order).
            _RESOLUTION_CACHE.pop(next(iter(_RESOLUTION_CACHE)))
        _RESOLUTION_CACHE[key] = json.loads(json.dumps(result))

    return result
