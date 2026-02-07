#!/usr/bin/env python3
"""
Module: config
Purpose: Configuration settings for AEGIS PFAS risk engine.
    Defines package paths, data file locations, risk thresholds, and
    confidence mappings used throughout the AEGIS system.

    Rev History:
        1.0.0 - Initial configuration module

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from pathlib import Path
from typing import Any, Dict

# Package paths
PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT / "data"
COMPOUNDS_DIR = DATA_DIR / "compounds"
PATHWAYS_DIR = DATA_DIR / "pathways"
REGULATIONS_DIR = DATA_DIR / "regulations"
EVIDENCE_DIR = DATA_DIR / "evidence"

# Evidence data files
PFAS_LIT_SUMMARY = EVIDENCE_DIR / "merged_evidence.json"  # Merged extraction + legacy
ELLIS_EVIDENCE = EVIDENCE_DIR / "ellis_thesis_evidence.json"
MANUAL_EVIDENCE = EVIDENCE_DIR / "manual_evidence.yaml"
TFA_DESTRUCTION_PAPERS = EVIDENCE_DIR / "tfa_destruction_papers.yaml"  # Verified DOI evidence for TFA destruction
TFA_COMPREHENSIVE_EVIDENCE = EVIDENCE_DIR / "tfa_comprehensive_evidence.yaml"  # Full regulatory/academic/industry evidence

# V2 curated extraction data
PFAS_FATE_V2_JSON = EVIDENCE_DIR / "pfas_fate_v2.json"
PFAS_FATE_V2_RAW = EVIDENCE_DIR / "pfas_fate_v2_raw.json"

# Regulatory data files
EPA_PFAS_CSV = REGULATIONS_DIR / "epa_pfas.csv"

# External EPA CompTox dataset (full 10,974+ compounds with SMILES)
EPA_COMPTOX_CSV = REGULATIONS_DIR / "epa_pfas.csv"
REGULATORY_FRAMEWORK_YAML = REGULATIONS_DIR / "regulatory_framework.yaml"
TFA_REGULATORY_ASSERTIONS = REGULATIONS_DIR / "tfa_regulatory_assertions.yaml"  # Comprehensive TFA regulatory status

# Pathway data files
DEGRADATION_PATHWAYS_EXTRACTED = PATHWAYS_DIR / "degradation_pathways_extracted.yaml"
DEGRADATION_PATHWAYS_LITERATURE = PATHWAYS_DIR / "degradation_pathways_literature.yaml"

# Literature corpus stats (from D:\chemours_PFAS\pfas lit)
LITERATURE_PAPER_COUNT = 328

# Risk thresholds
HIGH_TEMP_THRESHOLD_C = 800.0  # EPA incineration/fire scenario threshold

# Confidence mappings
CONFIDENCE_MAPPING: Dict[str, float] = {
    "low": 0.3,
    "medium": 0.6,
    "med": 0.6,
    "high": 0.9,
    "very_high": 0.95,
}

# Default evaluation parameters
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_RESULTS = 1000


def get_data_path(subdir: str = "") -> Path:
    """Get path to data directory or subdirectory."""
    if subdir:
        return DATA_DIR / subdir
    return DATA_DIR
