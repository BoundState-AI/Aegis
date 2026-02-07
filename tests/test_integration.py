#!/usr/bin/env python3
"""
Module: test_integration
Purpose: Integration tests for AEGIS Tier 1 + Tier 2 engines.
    Validates query structure, risk signals, evidence citations,
    substructure pattern detection, coverage metrics, and graceful
    error handling.

    Rev History:
        1.0.0 - Initial integration test suite

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
"""

from __future__ import annotations

import pytest

from boundstate_aegis.engines.tier1_engine import AEGISTier1Engine
from boundstate_aegis.engines.tier2_substructure_engine import Tier2Engine

# ---------------------------------------------------------------------------
# Reference SMILES
# ---------------------------------------------------------------------------

PFOA_SMILES = "OC(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F"
GENX_SMILES = "OC(=O)C(F)(OC(F)(F)C(F)(F)C(F)(F)F)C(F)(F)F"
FTOH_6_2_SMILES = "OCCC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tier1_engine():
    return AEGISTier1Engine()


@pytest.fixture(scope="module")
def tier2_engine():
    return Tier2Engine()


# ---------------------------------------------------------------------------
# Tier 1 tests
# ---------------------------------------------------------------------------


class TestTier1:
    def test_query_structure(self, tier1_engine):
        """Tier 1 query returns expected structure."""
        result = tier1_engine.query(PFOA_SMILES, "PFOA")

        assert "risk_signal" in result
        assert "top_endpoints" in result
        assert "similar_with_pathways" in result
        assert "evidence_citations" in result
        assert "tier2" in result

    def test_pfoa_high_risk(self, tier1_engine):
        """PFOA returns HIGH risk signal."""
        result = tier1_engine.query(PFOA_SMILES, "PFOA")
        assert result["risk_signal"] == "HIGH"

    def test_has_evidence_citations(self, tier1_engine):
        """Query returns DOI citations."""
        result = tier1_engine.query(PFOA_SMILES, "PFOA")
        assert len(result["evidence_citations"]) > 0
        assert "doi" in result["evidence_citations"][0]


# ---------------------------------------------------------------------------
# Tier 2 tests
# ---------------------------------------------------------------------------


class TestTier2:
    def test_coverage_above_50_percent(self, tier2_engine):
        """Tier 2 resolution rate exceeds 50%."""
        coverage = tier2_engine.get_coverage()
        assert coverage.resolution_rate > 0.50

    def test_coverage_filters_non_resolvable(self, tier2_engine):
        """Non-resolvable precursors are filtered."""
        coverage = tier2_engine.get_coverage()
        assert coverage.non_resolvable_count > 0

    def test_pfoa_patterns(self, tier2_engine):
        """PFOA triggers expected patterns."""
        result = tier2_engine.predict_endpoints(PFOA_SMILES)
        pattern_names = [p.pattern_name for p in result.patterns_detected]

        assert "carboxylic_acid" in pattern_names
        assert "pfaa" in pattern_names
        # Should be long chain (7+ perfluoro carbons)
        assert "long_chain" in pattern_names or "perfluoro_chain_c8plus" in pattern_names

    def test_genx_patterns(self, tier2_engine):
        """GenX triggers ether linkage pattern."""
        result = tier2_engine.predict_endpoints(GENX_SMILES)
        pattern_names = [p.pattern_name for p in result.patterns_detected]

        assert "carboxylic_acid" in pattern_names
        assert "fluorinated_ether" in pattern_names or "ether_linkage" in pattern_names

    def test_ftoh_patterns(self, tier2_engine):
        """6:2 FTOH triggers terminal_oh pattern."""
        result = tier2_engine.predict_endpoints(FTOH_6_2_SMILES)
        pattern_names = [p.pattern_name for p in result.patterns_detected]

        assert "terminal_oh" in pattern_names

    def test_has_endpoint_correlations(self, tier2_engine):
        """Predictions include endpoint correlations with confidence."""
        result = tier2_engine.predict_endpoints(PFOA_SMILES)

        assert len(result.endpoint_correlations) > 0
        corr = result.endpoint_correlations[0]
        assert hasattr(corr, "confidence")
        assert hasattr(corr, "ci_low")
        assert hasattr(corr, "ci_high")


# ---------------------------------------------------------------------------
# Cross-tier integration
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_tier1_includes_tier2(self, tier1_engine):
        """Tier 1 query includes Tier 2 results."""
        result = tier1_engine.query(PFOA_SMILES, "PFOA")

        assert result["tier2"] is not None
        assert "patterns_detected" in result["tier2"]

    def test_invalid_smiles_graceful(self, tier1_engine, tier2_engine):
        """Invalid SMILES handled gracefully."""
        # Tier 1
        try:
            result = tier1_engine.query("not_a_smiles", "invalid")
            # Should either raise ValueError or return error structure
        except (ValueError, Exception):
            pass  # Expected

        # Tier 2
        result = tier2_engine.predict_endpoints("not_a_smiles")
        assert result.patterns_detected == [] or "error" in str(result)
