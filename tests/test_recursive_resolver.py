#!/usr/bin/env python3
"""Tests for recursive regulatory resolver."""

from __future__ import annotations

from boundstate_aegis.engines.capability_registry import CapabilityRegistry
from boundstate_aegis.engines.product_manifest import ProductManifest
from boundstate_aegis.engines.recursive_resolver import UnresolvableCompound, resolve


def test_product_manifest_lookup() -> None:
    manifest = ProductManifest.load()
    hit = manifest.lookup_product("Opteon 1234yf")
    assert hit is not None
    assert hit.cas == "754-12-1"
    assert "HFO" in hit.compound_classes


def test_capability_registry_gap() -> None:
    registry = CapabilityRegistry.load()
    assert registry.has_client_capability("TFA", client="chemours") is False
    detail = registry.get_gap_detail("TFA", client="chemours")
    assert "no owned/licensed capability" in detail.lower() or "no known" in detail.lower()


def test_opteon_resolution_and_tree() -> None:
    result = resolve("Opteon 1234yf")
    assert result["query_compound"]["cas"] == "754-12-1"
    assert result["query_compound"]["resolution_method"] == "product_manifest"
    assert result["degradation_tree"]["total_nodes"] >= 1

    names = [n["compound"]["preferred_name"] for n in result["degradation_tree"]["nodes"]]
    assert any("tfa" in n.lower() for n in names)

    flag_types = {f["flag_type"] for f in result["threat_flags"]}
    assert "INHERITED_LIABILITY" in flag_types
    assert "DESTRUCTION_TECH_GAP" in flag_types


def test_cas_and_name_resolve_same_compound() -> None:
    left = resolve("Opteon 1234yf")
    right = resolve("754-12-1")
    assert left["query_compound"]["cas"] == right["query_compound"]["cas"]


def test_unresolvable_compound_raises() -> None:
    try:
        resolve("definitely_not_a_real_compound_xyz123")
        assert False, "Expected UnresolvableCompound"
    except UnresolvableCompound:
        pass


def test_determinism_excluding_runtime_metadata() -> None:
    first = resolve("Opteon 1234yf")
    second = resolve("Opteon 1234yf")
    for payload in (first, second):
        payload["metadata"].pop("resolved_at", None)
        payload["metadata"].pop("resolve_duration_ms", None)
    assert first == second


def test_traversal_caps() -> None:
    result = resolve("PTFE", max_nodes=3)
    assert result["degradation_tree"]["truncated"] is True
    assert result["degradation_tree"]["total_nodes"] <= 3


def test_metadata_fields_present() -> None:
    result = resolve("Opteon 1234yf")
    meta = result["metadata"]
    assert meta["resolver_version"]
    assert meta["graph_version"]
    assert meta["assertion_version"]
    assert meta["manifest_version"]
    assert meta["resolved_at"]
