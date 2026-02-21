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

import os
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

# APAC regulatory data
APAC_REGULATORY_ASSERTIONS = REGULATIONS_DIR / "apac_regulatory_assertions.yaml"
APAC_REG_DOCS_DIR = PACKAGE_ROOT.parent / "apac_reg_docs"
WESTERN_REGULATORY_ASSERTIONS = REGULATIONS_DIR / "western_regulatory_assertions.yaml"
PENDING_ASSERTIONS_DIR = REGULATIONS_DIR / "pending_assertions"

# Regulatory data files
EPA_PFAS_CSV = REGULATIONS_DIR / "epa_pfas.csv"

# External EPA CompTox dataset (full 10,974+ compounds with SMILES)
EPA_COMPTOX_CSV = REGULATIONS_DIR / "epa_pfas.csv"
REGULATORY_FRAMEWORK_YAML = REGULATIONS_DIR / "regulatory_framework.yaml"
TFA_REGULATORY_ASSERTIONS = REGULATIONS_DIR / "tfa_regulatory_assertions.yaml"  # Comprehensive TFA regulatory status
CHEMOURS_PRODUCT_MANIFEST = DATA_DIR / "chemours_product_manifest.yaml"
CAPABILITY_REGISTRY = DATA_DIR / "capability_registry.yaml"

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

# Regulatory intelligence quality gates (Chemours production mode)
REGULATORY_STRICT_MODE = os.getenv("AEGIS_REGULATORY_STRICT_MODE", "true").lower() in {
    "1", "true", "yes", "on",
}
REGULATORY_APAC_MIN_CONFIDENCE = float(
    os.getenv("AEGIS_REGULATORY_APAC_MIN_CONFIDENCE", "0.85")
)
REGULATORY_APAC_REQUIRE_PRIMARY_CITATION = os.getenv(
    "AEGIS_REGULATORY_APAC_REQUIRE_PRIMARY_CITATION", "true",
).lower() in {"1", "true", "yes", "on"}

# Monitoring L2-L4 pipeline configuration
MONITOR_DATA_DIR = PACKAGE_ROOT.parent / "monitor_data"
MONITOR_CONTENT_DIR = MONITOR_DATA_DIR / "content"
MONITOR_SNAPSHOTS_DIR = MONITOR_DATA_DIR / "snapshots"
MONITOR_SIGNALS_FILE = MONITOR_DATA_DIR / "signals.json"
MONITOR_DIGESTS_DIR = MONITOR_DATA_DIR / "digests"
CLIENT_PROFILE = PACKAGE_ROOT / "monitoring" / "client_profiles" / "chemours.yaml"
MONITOR_SNAPSHOT_RETENTION_MONTHS = int(
    os.getenv("AEGIS_MONITOR_SNAPSHOT_RETENTION_MONTHS", "24")
)
TRIAGE_MODEL = os.getenv("AEGIS_TRIAGE_MODEL", "claude-haiku-4-5-20251001")
ANALYST_MODEL = os.getenv("AEGIS_ANALYST_MODEL", "claude-sonnet-4-6")
TRIAGE_TOKEN_CAP = int(os.getenv("AEGIS_TRIAGE_TOKEN_CAP", "4000"))
MONITOR_STRICT_AI_MODE = os.getenv("AEGIS_MONITOR_STRICT_AI_MODE", "true").lower() in {
    "1", "true", "yes", "on",
}
MONITOR_RUN_LOCK_NAME = os.getenv("AEGIS_MONITOR_RUN_LOCK_NAME", "aegis_monitor_run")
MONITOR_RUN_LOCK_TTL_SECONDS = int(os.getenv("AEGIS_MONITOR_RUN_LOCK_TTL_SECONDS", "5400"))

# Monitor API auth / RBAC
MONITOR_API_AUTH_ENABLED = os.getenv("AEGIS_MONITOR_API_AUTH_ENABLED", "true").lower() in {
    "1", "true", "yes", "on",
}
# Format: "key1:viewer,key2:operator,key3:approver,key4:admin"
MONITOR_API_KEYS = os.getenv("AEGIS_MONITOR_API_KEYS", "")
MONITOR_API_RATE_LIMIT_PER_MIN = int(os.getenv("AEGIS_MONITOR_API_RATE_LIMIT_PER_MIN", "120"))
# Optional comma-separated CIDRs to restrict monitor control-plane API access.
MONITOR_API_ALLOWLIST_CIDRS = os.getenv("AEGIS_MONITOR_API_ALLOWLIST_CIDRS", "")
MONITOR_API_MANUAL_RUN_ENABLED = os.getenv("AEGIS_MONITOR_API_MANUAL_RUN_ENABLED", "false").lower() in {
    "1", "true", "yes", "on",
}

# Critical alert fallback channels
MONITOR_ALERT_EMAIL_ENABLED = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_ENABLED", "false").lower() in {
    "1", "true", "yes", "on",
}
MONITOR_ALERT_EMAIL_SMTP_HOST = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_SMTP_HOST", "")
MONITOR_ALERT_EMAIL_SMTP_PORT = int(os.getenv("AEGIS_MONITOR_ALERT_EMAIL_SMTP_PORT", "587"))
MONITOR_ALERT_EMAIL_SMTP_USER = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_SMTP_USER", "")
MONITOR_ALERT_EMAIL_SMTP_PASSWORD = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_SMTP_PASSWORD", "")
MONITOR_ALERT_EMAIL_USE_TLS = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_USE_TLS", "true").lower() in {
    "1", "true", "yes", "on",
}
MONITOR_ALERT_EMAIL_FROM = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_FROM", "")
# Comma-delimited list.
MONITOR_ALERT_EMAIL_TO = os.getenv("AEGIS_MONITOR_ALERT_EMAIL_TO", "")
MONITOR_PAGERDUTY_ROUTING_KEY = os.getenv("AEGIS_MONITOR_PAGERDUTY_ROUTING_KEY", "")

# Assertion governance persistence (source-of-truth store).
AEGIS_ASSERTION_DB_PATH = os.getenv(
    "AEGIS_ASSERTION_DB_PATH",
    str(MONITOR_DATA_DIR / "assertions.db"),
)

# Third-party proxy governance controls.
MONITOR_PROXY_ENABLED = os.getenv("AEGIS_MONITOR_PROXY_ENABLED", "true").lower() in {
    "1", "true", "yes", "on",
}
# Comma-separated host allowlist for proxy fallback.
MONITOR_PROXY_ALLOWLIST = os.getenv(
    "AEGIS_MONITOR_PROXY_ALLOWLIST",
    "echa.europa.eu,www.echa.europa.eu,www.michigan.gov,michigan.gov,www.oecd.org,oecd.org",
)


def get_data_path(subdir: str = "") -> Path:
    """Get path to data directory or subdirectory."""
    if subdir:
        return DATA_DIR / subdir
    return DATA_DIR
