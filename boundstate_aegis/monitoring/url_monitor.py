#!/usr/bin/env python3
"""
Module: url_monitor
Purpose: Daily regulatory URL change detection for AEGIS.
    Fetches monitored government and aggregator pages, hashes content,
    compares against stored state, and alerts via Slack webhook when
    changes are detected.

    Designed to run as a Railway cron worker (0 6 * * * UTC).

    Rev History:
        1.0.0 - Initial monitor with 26 URLs across 7 APAC jurisdictions

BoundState AI 2026
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Co-Authored-By: Claude Opus 4.6 (Beth) <noreply@anthropic.com>
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

import requests
import urllib3

from boundstate_aegis.config import (
    MONITOR_PROXY_ALLOWLIST,
    MONITOR_PROXY_ENABLED,
    MONITOR_RUN_LOCK_NAME,
    MONITOR_RUN_LOCK_TTL_SECONDS,
)

from .alerts import build_signal_slack_payload, dispatch_critical_fallback, route_for_impact
from .diff import generate_diff
from .extract import extract_text
from .impact_assessor import ImpactAssessor
from .models import ContentSnapshot, RegulatorySignal
from .normalize import content_hash as normalized_content_hash
from .normalize import normalize_text
from .policies import evaluate_trigger, find_keyword_hits
from .signal_analyzer import SignalAnalyzer
from .source_policy import RunProfile, classification_summary, classify_source, select_sources
from .stores import RunLockStore, SignalStore, SnapshotStore, dataclass_to_plain, source_id_for_url

# Some government sources serve invalid cert chains; source-specific overrides
# are handled via MonitoredURL.insecure_ssl without polluting logs.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("aegis.monitor")

# Persistent storage — Railway volume mount or local directory
HASH_STORE_DIR = Path(os.getenv("MONITOR_STORE_DIR", "./monitor_data"))
HASH_STORE_FILE = HASH_STORE_DIR / "url_hashes.json"
ALERT_LOG_FILE = HASH_STORE_DIR / "alert_history.json"
HASH_STORE_SECRET = os.getenv("AEGIS_HASH_STORE_SECRET", "")

# Slack webhook for alerts
SLACK_WEBHOOK_URL = os.getenv("MONITOR_SLACK_WEBHOOK", "")

# Request settings
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
USER_AGENT = "BoundState-AEGIS-Monitor/1.0 (regulatory-change-detection; contact@boundstate.ai)"
PROXY_ALLOWLIST_HOSTS = {host.strip().lower() for host in MONITOR_PROXY_ALLOWLIST.split(",") if host.strip()}

# Domain-specific timeout overrides — Japanese and Australian government
# servers are notoriously slow for international requests.  The default
# 15 s is plenty for US/EU sources but regularly causes false-negative
# timeouts on METI, NITE, NHMRC and DCCEEW.  These overrides let us
# be patient where it matters without slowing every cycle.
DOMAIN_TIMEOUT_OVERRIDES: Dict[str, int] = {
    # Japan — METI press releases, NITE databases, MOE portals
    "www.meti.go.jp":     45,
    "www.nite.go.jp":     45,
    "www.env.go.jp":      45,
    "www.caa.go.jp":      45,
    "elaws.e-gov.go.jp":  45,
    # Australia — NHMRC guidelines, DCCEEW NEMP / PFAS landing
    "www.nhmrc.gov.au":           45,
    "guidelines.nhmrc.gov.au":    45,
    "www.dcceew.gov.au":          45,
    "consult.dcceew.gov.au":      30,
    # South Korea — K-REACH, MFDS
    "kreach.me.go.kr":    30,
    "www.mfds.go.kr":     30,
    # India — CPCB has chronic SSL/connectivity issues
    "cpcb.nic.in":        30,
    "fssai.gov.in":       30,
    # China — MEE portal behind GFW, variable latency
    "www.mee.gov.cn":     30,
}


def _timeout_for_url(url: str) -> int:
    """Return the appropriate timeout for a URL based on domain overrides."""
    host = urlparse(url).netloc.lower()
    return DOMAIN_TIMEOUT_OVERRIDES.get(host, REQUEST_TIMEOUT)


# Rate limiting — be polite to government servers
REQUEST_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------------
# URL Registry
# ---------------------------------------------------------------------------

class URLTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DOCUMENT = "document"


class URLStatus(str, Enum):
    OK = "ok"
    CHANGED = "changed"
    NEW = "new"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    SSL_ERROR = "ssl_error"
    NOT_FOUND = "not_found"
    DEGRADED = "degraded"


@dataclass
class MonitoredURL:
    url: str
    tier: URLTier
    country: str
    label: str
    known_blocked: bool = False
    insecure_ssl: bool = False


# Government & regulatory primary sources
MONITORED_URLS: List[MonitoredURL] = [

    # =========================================================================
    # NORTH AMERICA — US Federal
    # =========================================================================

    # ---- US EPA ----
    MonitoredURL(
        url="https://www.epa.gov/pfas",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — PFAS Strategic Roadmap landing page",
    ),
    MonitoredURL(
        url="https://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — SDWA PFAS drinking water rule (MCLs)",
    ),
    MonitoredURL(
        url="https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — TSCA PFAS reporting and testing",
    ),
    MonitoredURL(
        url="https://www.epa.gov/superfund/questions-and-answers-about-designation-pfoa-and-pfos-hazardous-substances-under-cercla",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — CERCLA PFAS hazardous substance designation",
    ),
    MonitoredURL(
        url="https://www.govinfo.gov/content/pkg/FR-2024-04-26/pdf/2024-07773.pdf",
        tier=URLTier.DOCUMENT, country="US",
        label="Federal Register/GovInfo — Final PFAS NPDWR rule (PDF, April 2024)",
    ),
    MonitoredURL(
        url="https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=environmental-protection-agency&conditions%5Bterm%5D=PFAS&order=newest",
        tier=URLTier.PRIMARY, country="US",
        label="Federal Register API — EPA PFAS rulemaking feed",
    ),
    MonitoredURL(
        url="https://comptox.epa.gov/dashboard/chemical-lists/PFASMASTER",
        tier=URLTier.PRIMARY, country="US",
        label="EPA CompTox — PFAS Master List",
    ),

    # ---- US States ----
    MonitoredURL(
        url="https://www.waterboards.ca.gov/drinking_water/certlic/drinkingwater/pfas.html",
        tier=URLTier.PRIMARY, country="US-CA",
        label="California SWRCB — PFAS drinking water program",
    ),
    MonitoredURL(
        url="https://oehha.ca.gov/proposition-65/chemicals/perfluorooctanoic-acid-pfoa",
        tier=URLTier.PRIMARY, country="US-CA",
        label="California Prop 65 — PFOA listing",
    ),
    MonitoredURL(
        url="https://oehha.ca.gov/proposition-65/chemicals/perfluorooctane-sulfonate-pfos",
        tier=URLTier.PRIMARY, country="US-CA",
        label="California Prop 65 — PFOS listing",
    ),
    MonitoredURL(
        url="https://deq.nc.gov/news/key-issues/genx-investigation",
        tier=URLTier.PRIMARY, country="US-NC",
        label="North Carolina DEQ — GenX investigation",
    ),
    MonitoredURL(
        url="https://www.michigan.gov/pfasresponse",
        tier=URLTier.PRIMARY, country="US-MI",
        label="Michigan PFAS Action Response Team",
    ),
    MonitoredURL(
        url="https://ecology.wa.gov/waste-toxics/reducing-toxic-chemicals/addressing-priority-toxic-chemicals/pfas",
        tier=URLTier.PRIMARY, country="US-WA",
        label="Washington Ecology — PFAS program",
    ),
    MonitoredURL(
        url="https://dec.ny.gov/pfas",
        tier=URLTier.PRIMARY, country="US-NY",
        label="New York DEC — PFAS in drinking water",
    ),
    MonitoredURL(
        url="https://www.nj.gov/dep/watersupply/pfas/",
        tier=URLTier.PRIMARY, country="US-NJ",
        label="New Jersey DEP — PFAS drinking water program",
    ),
    MonitoredURL(
        url="https://www.courtlistener.com/api/rest/v4/search/?q=PFAS",
        tier=URLTier.PRIMARY, country="US-LIT",
        label="CourtListener — PFAS litigation docket tracker",
    ),

    # =========================================================================
    # EUROPE
    # =========================================================================

    # ---- EU REACH / ECHA ----
    MonitoredURL(
        url="https://echa.europa.eu/registry-of-restriction-intentions/-/registry-of-restriction-intentions/q?p_p_id=com_liferay_portal_search_web_portlet_SearchPortlet_INSTANCE_restriction_intentions",
        tier=URLTier.PRIMARY, country="EU",
        label="ECHA — Registry of restriction intentions (universal PFAS)",
    ),
    MonitoredURL(
        url="https://echa.europa.eu/substances-of-very-high-concern-identification/-/substance-designation/-/substance/100.001.017",
        tier=URLTier.PRIMARY, country="EU",
        label="ECHA — PFOA SVHC identification",
    ),
    MonitoredURL(
        url="https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas",
        tier=URLTier.PRIMARY, country="EU",
        label="ECHA — PFAS hot topics overview",
    ),
    MonitoredURL(
        url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R1021",
        tier=URLTier.PRIMARY, country="EU",
        label="EU POPs Regulation (2019/1021) — PFOA/PFOS listings",
    ),

    # ---- EU Drinking Water ----
    MonitoredURL(
        url="https://eur-lex.europa.eu/eli/dir/2020/2184/oj",
        tier=URLTier.PRIMARY, country="EU",
        label="EU Drinking Water Directive 2020/2184 (PFAS sum 0.5 µg/L)",
    ),

    # ---- UK (post-Brexit, independent UK REACH) ----
    MonitoredURL(
        url="https://www.hse.gov.uk/reach/",
        tier=URLTier.PRIMARY, country="UK",
        label="HSE — UK REACH regulatory framework",
    ),
    MonitoredURL(
        url="https://www.gov.uk/government/publications/environmental-risk-evaluation-reports-per-and-polyfluoroalkyl-substances-pfas",
        tier=URLTier.PRIMARY, country="UK",
        label="UK Gov — PFAS/PFOS/PFOA general information",
    ),
    MonitoredURL(
        url="https://www.gov.uk/government/publications/pfas-plan/pfas-plan-building-a-safer-future-together",
        tier=URLTier.PRIMARY, country="UK",
        label="UK Defra — PFAS policy collection",
    ),

    # ---- Denmark (co-authored EU universal PFAS restriction) ----
    MonitoredURL(
        url="https://mst.dk/erhverv/sikker-kemi/kemikalier/fokus-paa-saerlige-stoffer/pfas",
        tier=URLTier.PRIMARY, country="Denmark",
        label="Danish EPA — PFAS focus (food contact ban pioneer)",
    ),

    # ---- Norway (co-authored EU universal PFAS restriction) ----
    MonitoredURL(
        url="https://www.miljodirektoratet.no/sok/?q=PFAS",
        tier=URLTier.PRIMARY, country="Norway",
        label="Norwegian Environment Agency — PFAS restriction",
    ),

    # ---- Germany (co-authored EU universal PFAS restriction) ----
    MonitoredURL(
        url="https://www.umweltbundesamt.de/en/search?query=PFAS",
        tier=URLTier.PRIMARY, country="Germany",
        label="UBA — German Environment Agency PFAS restriction proposals",
    ),

    # ---- Sweden (co-authored EU universal PFAS restriction) ----
    MonitoredURL(
        url="https://www.kemi.se/en/chemical-substances-and-materials/highly-fluorinated-substances",
        tier=URLTier.PRIMARY, country="Sweden",
        label="KEMI — Swedish Chemicals Agency PFAS overview",
    ),

    # ---- Netherlands (co-authored EU universal PFAS restriction) ----
    MonitoredURL(
        url="https://www.rivm.nl/en/pfas",
        tier=URLTier.PRIMARY, country="Netherlands",
        label="RIVM — Dutch PFAS risk assessment and policy",
    ),

    # =========================================================================
    # CANADA
    # =========================================================================
    MonitoredURL(
        url="https://www.canada.ca/en/health-canada/services/chemical-substances/other-chemical-substances-interest/per-polyfluoroalkyl-substances.html",
        tier=URLTier.PRIMARY, country="Canada",
        label="Health Canada — PFAS overview and risk management",
    ),
    MonitoredURL(
        url="https://www.canada.ca/en/environment-climate-change/services/management-toxic-substances/list-canadian-environmental-protection-act/perfluorooctane-sulfonate.html",
        tier=URLTier.PRIMARY, country="Canada",
        label="ECCC — PFOS under CEPA toxic substances",
    ),
    MonitoredURL(
        url="https://gazette.gc.ca/index-eng.html",
        tier=URLTier.PRIMARY, country="Canada",
        label="Canada Gazette — Federal regulatory publication",
    ),

    # =========================================================================
    # OCEANIA — New Zealand
    # =========================================================================
    MonitoredURL(
        url="https://www.taumataarowai.govt.nz/",
        tier=URLTier.PRIMARY, country="New Zealand",
        label="Taumata Arowai — NZ Drinking Water regulator",
    ),
    MonitoredURL(
        url="https://www.epa.govt.nz/industry-areas/hazardous-substances/",
        tier=URLTier.PRIMARY, country="New Zealand",
        label="NZ EPA — Hazardous substances (PFAS classification)",
    ),

    # =========================================================================
    # LATIN AMERICA
    # =========================================================================
    MonitoredURL(
        url="https://www.gov.br/anvisa/pt-br",
        tier=URLTier.PRIMARY, country="Brazil",
        label="ANVISA — Brazil health regulatory agency (PFAS emerging)",
    ),

    # =========================================================================
    # INTERNATIONAL
    # =========================================================================
    MonitoredURL(
        url="http://chm.pops.int/TheConvention/ThePOPs/TheNewPOPs/tabid/2511/Default.aspx",
        tier=URLTier.PRIMARY, country="International",
        label="Stockholm Convention — New POPs listings (PFOA/PFOS/PFHxS)",
    ),
    MonitoredURL(
        url="http://chm.pops.int/Implementation/NationalImplementationPlans/NIPTransmission/tabid/253/Default.aspx",
        tier=URLTier.PRIMARY, country="International",
        label="Stockholm Convention — National Implementation Plans",
    ),
    MonitoredURL(
        url="https://www.who.int/teams/environment-climate-change-and-health/water-sanitation-and-health/chemical-hazards-in-drinking-water/per-and-polyfluoroalkyl-substances",
        tier=URLTier.PRIMARY, country="International",
        label="WHO — PFAS in drinking water guidance",
    ),
    MonitoredURL(
        url="https://www.oecd.org/chemicalsafety/portal-perfluorinated-chemicals/",
        tier=URLTier.PRIMARY, country="International",
        label="OECD — PFAS portal and policy coordination",
    ),
    MonitoredURL(
        url="https://www.naag.org/attorneys-general/attorney-general-journal/?s=pfas",
        tier=URLTier.SECONDARY, country="US",
        label="NAAG — State Attorney General PFAS enforcement coverage",
    ),
    MonitoredURL(
        url="https://legiscan.com/gaits/search?keyword=PFAS",
        tier=URLTier.SECONDARY, country="US",
        label="LegiScan — State PFAS bill tracking",
    ),
    MonitoredURL(
        url="https://echa.europa.eu/search-for-chemicals?query=tfa",
        tier=URLTier.SECONDARY, country="EU",
        label="ECHA — TFA related chemical search tracker",
    ),

    # =========================================================================
    # APAC — Japan
    # =========================================================================

    # ---- Japan ----
    MonitoredURL(
        url="https://www.nite.go.jp/en/chem/index.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="NITE — Chemical Management English hub (J-CHECK, CSCL, CHRIP)",
    ),
    MonitoredURL(
        url="https://elaws.e-gov.go.jp/document?lawid=348AC0000000117",
        tier=URLTier.PRIMARY, country="Japan",
        label="e-Gov Laws — Japan CSCL legal text",
    ),
    MonitoredURL(
        url="https://www.env.go.jp/water/",
        tier=URLTier.PRIMARY, country="Japan",
        label="Japan MOE — Water Quality Standards portal",
    ),
    MonitoredURL(
        url="https://www.caa.go.jp/",
        tier=URLTier.PRIMARY, country="Japan",
        label="Japan CAA — Consumer Affairs Agency (food contact)",
    ),
    MonitoredURL(
        url="https://www.env.go.jp/en/headline/790.html",
        tier=URLTier.SECONDARY, country="Japan",
        label="Japan MOE English — J-CHECK chemical database announcement",
    ),
    MonitoredURL(
        url="https://www.env.go.jp/chemi/",
        tier=URLTier.PRIMARY, country="Japan",
        label="Japan MOE — Chemical management portal",
    ),
    MonitoredURL(
        url="https://www.env.go.jp/water/pfas.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="Japan MOE — PFAS in water page",
    ),

    # ---- South Korea ----
    MonitoredURL(
        url="https://kreach.me.go.kr/",
        tier=URLTier.PRIMARY, country="South Korea",
        label="Korea K-REACH — Chemical registration portal",
    ),
    MonitoredURL(
        url="https://www.mfds.go.kr/index.do",
        tier=URLTier.PRIMARY, country="South Korea",
        label="Korea MFDS — Ministry of Food and Drug Safety",
    ),

    # ---- China ----
    MonitoredURL(
        url="https://www.mee.gov.cn/",
        tier=URLTier.PRIMARY, country="China",
        label="China MEE — Ministry of Ecology and Environment portal",
    ),

    # ---- Australia ----
    MonitoredURL(
        url="https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC ADWG — Main drinking water guideline",
    ),
    MonitoredURL(
        url="https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC ADWG — Part 5 chemical characteristics",
    ),
    MonitoredURL(
        url="https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5/physical-chemical-characteristics/cas-numbers-1763-23-1-pfos-335-67-1-pfoa-355-46-4-pfhxs",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC ADWG — PFAS guideline values (PFOS/PFOA/PFHxS)",
    ),
    MonitoredURL(
        url="https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5/physical-chemical-characteristics",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC ADWG — Part 5 physical/chemical characteristics",
    ),
    MonitoredURL(
        url="https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-1",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC ADWG — Part 1 framework",
    ),
    MonitoredURL(
        url="https://consult.dcceew.gov.au/nemp-pfas",
        tier=URLTier.PRIMARY, country="Australia",
        label="DCCEEW Consult — PFAS NEMP coordination and consultation",
    ),

    # ---- Singapore ----
    MonitoredURL(
        url="https://www.nea.gov.sg/docs/default-source/default-document-library/phase-out-of-fire-fighting-foams-containing-pfas-chemicals-listed-under-the-stockholm-convention_15mar24.pdf",
        tier=URLTier.DOCUMENT, country="Singapore",
        label="NEA Circular NEA/HS/6.6 — AFFF PFAS phase-out (PDF)",
    ),
    MonitoredURL(
        url="https://www.nea.gov.sg/docs/default-source/hs/industry-guideline-on-the-phase-out-of-pfas-containing-firefighting-foams.pdf",
        tier=URLTier.DOCUMENT, country="Singapore",
        label="NEA — Industry guideline PFAS firefighting foams (PDF)",
    ),

    # ---- Taiwan ----
    MonitoredURL(
        url="https://www.cha.gov.tw/fp-193-6212-09aa4-2.html",
        tier=URLTier.PRIMARY, country="Taiwan",
        label="Taiwan Chemicals Administration — PFHxS designation",
    ),

    # ---- India ----
    MonitoredURL(
        url="https://cpcb.nic.in/",
        tier=URLTier.PRIMARY, country="India",
        label="India CPCB — Central Pollution Control Board portal",
        insecure_ssl=True,
    ),
    MonitoredURL(
        url="https://fssai.gov.in/notifications.php",
        tier=URLTier.PRIMARY, country="India",
        label="India FSSAI — Food Safety notifications (PFAS/BPA packaging draft)",
    ),
]

# Secondary / aggregator sources
SECONDARY_URLS: List[MonitoredURL] = [
    # ---- US / Global aggregators ----
    MonitoredURL(
        url="https://www.epa.gov/newsroom/browse-news-releases?search_api_fulltext=pfas",
        tier=URLTier.SECONDARY, country="US",
        label="EPA — PFAS press releases feed",
    ),
    MonitoredURL(
        url="https://www.saferstates.org/priorities/pfas/",
        tier=URLTier.SECONDARY, country="US",
        label="Safer States — US state PFAS legislation tracker",
    ),
    MonitoredURL(
        url="https://pfas-1.itrcweb.org/",
        tier=URLTier.SECONDARY, country="US",
        label="ITRC — PFAS technical/regulatory guidance",
    ),

    # ---- EU aggregators ----
    MonitoredURL(
        url="https://www.eea.europa.eu/en/search?SearchableText=PFAS",
        tier=URLTier.SECONDARY, country="EU",
        label="EEA — PFAS search and news index",
    ),

    # ---- APAC aggregators ----
    MonitoredURL(
        url="https://enviliance.com/regions/east-asia/jp",
        tier=URLTier.SECONDARY, country="Japan",
        label="Enviliance Asia — Japan regulatory tracker",
    ),
    MonitoredURL(
        url="https://enviliance.com/regions/east-asia/kr",
        tier=URLTier.SECONDARY, country="South Korea",
        label="Enviliance Asia — Korea regulatory tracker",
    ),
    MonitoredURL(
        url="https://enviliance.com/regions/east-asia/cn",
        tier=URLTier.SECONDARY, country="China",
        label="Enviliance Asia — China regulatory tracker",
    ),
    MonitoredURL(
        url="https://www.chemradar.com/en/lawinfo/news/",
        tier=URLTier.SECONDARY, country="China",
        label="ChemRadar/CIRS — China regulatory news (MEE proxy, English)",
    ),
    MonitoredURL(
        url="https://www.mee.gov.cn/ywgz/gtfwyhxpgl/",
        tier=URLTier.SECONDARY, country="China",
        label="China MEE — Solid waste and chemicals management",
    ),
    MonitoredURL(
        url="https://www.ul.com/news",
        tier=URLTier.SECONDARY, country="APAC",
        label="UL Solutions — Regulatory news (Taiwan coverage)",
    ),
    MonitoredURL(
        url="https://www.dnv.com/news/",
        tier=URLTier.SECONDARY, country="APAC",
        label="DNV — Maritime/industrial PFAS regulatory news",
    ),
]

ALL_URLS = MONITORED_URLS + SECONDARY_URLS


# ---------------------------------------------------------------------------
# Hash Store — persistent state between runs
# ---------------------------------------------------------------------------

@dataclass
class URLHashRecord:
    url: str
    hash: str
    last_checked: str
    last_changed: Optional[str]
    status: str
    content_length: int = 0
    check_count: int = 0
    change_count: int = 0


def load_hash_store() -> Dict[str, URLHashRecord]:
    if not HASH_STORE_FILE.exists():
        logger.info("No existing hash store — first run")
        return {}
    try:
        with open(HASH_STORE_FILE, encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict) and "data" in loaded and "hmac" in loaded:
            raw = loaded["data"]
            if HASH_STORE_SECRET:
                canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                expected = hmac.new(
                    HASH_STORE_SECRET.encode("utf-8"),
                    canonical.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if not hmac.compare_digest(str(loaded.get("hmac", "")), expected):
                    raise RuntimeError("Hash store integrity check failed (HMAC mismatch)")
        elif isinstance(loaded, dict):
            raw = loaded
            if HASH_STORE_SECRET:
                raise RuntimeError("Hash store is unsigned while AEGIS_HASH_STORE_SECRET is configured")
        else:
            raise RuntimeError("Unexpected hash store format")

        store = {}
        for url, data in raw.items():
            store[url] = URLHashRecord(
                url=data["url"],
                hash=data["hash"],
                last_checked=data["last_checked"],
                last_changed=data.get("last_changed"),
                status=data.get("status", "ok"),
                content_length=data.get("content_length", 0),
                check_count=data.get("check_count", 0),
                change_count=data.get("change_count", 0),
            )
        logger.info(f"Loaded hash store: {len(store)} URLs tracked")
        return store
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Failed to load hash store: {e}")
        return {}


def save_hash_store(store: Dict[str, URLHashRecord]) -> None:
    HASH_STORE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        raw = {url: asdict(record) for url, record in store.items()}
        with open(HASH_STORE_FILE, "w", encoding="utf-8") as f:
            if HASH_STORE_SECRET:
                canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                signature = hmac.new(
                    HASH_STORE_SECRET.encode("utf-8"),
                    canonical.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                json.dump({"data": raw, "hmac": signature}, f, indent=2, default=str)
            else:
                json.dump(raw, f, indent=2, default=str)
        logger.info(f"Saved hash store: {len(store)} URLs")
    except Exception as e:
        logger.error(f"Failed to save hash store: {e}")


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

@dataclass
class FetchResult:
    url: str
    status: URLStatus
    content_hash: Optional[str] = None
    content_length: int = 0
    raw_content: bytes = b""
    content_type: str = ""
    response_headers: Dict[str, str] = field(default_factory=dict)
    fetched_via: str = "direct"
    error: Optional[str] = None
    http_status: Optional[int] = None
    elapsed_ms: int = 0


def _blocked_proxy_url(url: str) -> Optional[str]:
    """Return proxy URL for sources that consistently block direct requests."""
    if not MONITOR_PROXY_ENABLED:
        return None
    host = urlparse(url).netloc.lower()
    if host in PROXY_ALLOWLIST_HOSTS:
        stripped = url.split("://", 1)[-1]
        return f"https://r.jina.ai/http://{stripped}"
    return None


def _proxy_fetch(url: str, *, headers: Dict[str, str], start: float) -> Optional[FetchResult]:
    proxy_url = _blocked_proxy_url(url)
    if not proxy_url:
        return None

    try:
        proxy_resp = requests.get(
            proxy_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        if proxy_resp.status_code != 200:
            return None
        content_hash = hashlib.sha256(proxy_resp.content).hexdigest()
        response_headers = dict(proxy_resp.headers)
        response_headers["x-aegis-fetched-via"] = "r.jina.ai"
        response_headers["x-aegis-source-url"] = url
        return FetchResult(
            url=url,
            status=URLStatus.OK,
            content_hash=content_hash,
            content_length=len(proxy_resp.content),
            raw_content=proxy_resp.content,
            content_type=proxy_resp.headers.get("content-type", ""),
            response_headers=response_headers,
            fetched_via="proxy:r.jina.ai",
            http_status=proxy_resp.status_code,
            elapsed_ms=elapsed,
        )
    except requests.RequestException:
        return None


def fetch_url(entry: MonitoredURL) -> FetchResult:
    url = entry.url
    headers = {"User-Agent": USER_AGENT}
    start = time.monotonic()
    timeout = _timeout_for_url(url)

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, headers=headers,
                timeout=timeout,
                allow_redirects=True,
                verify=not entry.insecure_ssl,
            )
            elapsed = int((time.monotonic() - start) * 1000)

            if resp.status_code == 403:
                fallback = _proxy_fetch(url, headers=headers, start=start)
                if fallback:
                    return fallback
                return FetchResult(
                    url=url, status=URLStatus.BLOCKED,
                    error="403 Forbidden", http_status=403, elapsed_ms=elapsed,
                )
            elif resp.status_code == 404:
                return FetchResult(
                    url=url, status=URLStatus.NOT_FOUND,
                    error="404 Not Found — URL may have moved",
                    http_status=404, elapsed_ms=elapsed,
                )
            elif resp.status_code >= 500:
                if attempt < MAX_RETRIES:
                    logger.warning(f"  Retry {attempt+1}/{MAX_RETRIES} for {url} (HTTP {resp.status_code})")
                    time.sleep(2)
                    continue
                return FetchResult(
                    url=url, status=URLStatus.DEGRADED,
                    error=f"HTTP {resp.status_code} after {MAX_RETRIES+1} attempts",
                    http_status=resp.status_code, elapsed_ms=elapsed,
                )
            elif not (200 <= resp.status_code < 300):
                return FetchResult(
                    url=url, status=URLStatus.FAILED,
                    error=f"HTTP {resp.status_code}",
                    http_status=resp.status_code, elapsed_ms=elapsed,
                )

            content_hash = hashlib.sha256(resp.content).hexdigest()
            return FetchResult(
                url=url, status=URLStatus.OK,
                content_hash=content_hash,
                content_length=len(resp.content),
                raw_content=resp.content,
                content_type=resp.headers.get("content-type", ""),
                response_headers=dict(resp.headers),
                fetched_via="direct",
                http_status=200, elapsed_ms=elapsed,
            )

        except requests.exceptions.SSLError as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(
                url=url, status=URLStatus.SSL_ERROR,
                error=str(e)[:200], elapsed_ms=elapsed,
            )
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                logger.warning(f"  Timeout retry {attempt+1}/{MAX_RETRIES} for {url} (timeout={timeout}s)")
                continue
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(
                url=url, status=URLStatus.TIMEOUT,
                error=f"Timeout after {timeout}s x {MAX_RETRIES+1} attempts",
                elapsed_ms=elapsed,
            )
        except requests.exceptions.ConnectionError as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"  Connection retry {attempt+1}/{MAX_RETRIES} for {url}")
                time.sleep(2)
                continue
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(
                url=url, status=URLStatus.FAILED,
                error=f"Connection failed: {str(e)[:200]}",
                elapsed_ms=elapsed,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(
                url=url, status=URLStatus.FAILED,
                error=f"Unexpected: {str(e)[:200]}",
                elapsed_ms=elapsed,
            )

    return FetchResult(url=url, status=URLStatus.FAILED, error="Exhausted retries")


# ---------------------------------------------------------------------------
# Alert Engine — Slack webhook
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    url: str
    label: str
    country: str
    tier: str
    status: str
    detail: str
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None


def build_slack_payload(alerts: List[Alert], summary: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    change_count = sum(1 for a in alerts if a.status == "changed")
    error_count = sum(1 for a in alerts if a.status != "changed")
    header = f"🔔 AEGIS Regulatory Monitor — {now}"
    if change_count:
        header += f"\n*{change_count} content change(s) detected*"
    if error_count:
        header += f"\n⚠️ {error_count} URL issue(s)"

    blocks: List[Dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": "AEGIS Regulatory Monitor"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": header}},
        {"type": "divider"},
    ]

    changes = [a for a in alerts if a.status == "changed"]
    errors = [a for a in alerts if a.status != "changed"]

    for a in changes:
        flag = "🟢" if a.tier == "primary" else "🔵"
        hash_info = ""
        if a.old_hash and a.new_hash:
            hash_info = f"\n`{a.old_hash[:12]}…` → `{a.new_hash[:12]}…`"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{flag} *{a.label}* ({a.country})\n<{a.url}|View page>{hash_info}"},
        })

    if errors:
        blocks.append({"type": "divider"})
        for a in errors:
            emoji = {"not_found": "❌", "degraded": "🟡", "ssl_error": "🔴", "blocked": "🚫"}.get(a.status, "⚠️")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{emoji} *{a.label}* — {a.status}\n{a.detail}"},
            })

    blocks.append({"type": "divider"})
    signal_count = int(summary.get("signals", 0))
    noise_count = int(summary.get("noise", 0))
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": (
            f"Checked {summary['total']} URLs | "
            f"OK: {summary['ok']} | Changed: {summary['changed']} | "
            f"Noise: {noise_count} | Signals: {signal_count} | "
            f"Blocked: {summary['blocked']} | Errors: {summary['errors']} | "
            f"Duration: {summary['duration_s']:.1f}s"
        )}],
    })

    return {"blocks": blocks}


def send_slack_alert(alerts: List[Alert], summary: Dict[str, Any]) -> bool:
    if not SLACK_WEBHOOK_URL:
        logger.warning("No MONITOR_SLACK_WEBHOOK configured — skipping Slack alert")
        return False
    payload = build_slack_payload(alerts, summary)
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Slack alert sent: {len(alerts)} alert(s)")
            return True
        else:
            logger.error(f"Slack webhook returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Slack webhook failed: {e}")
        return False


def send_intelligence_signal_alert(signal: RegulatorySignal) -> bool:
    if not SLACK_WEBHOOK_URL:
        return False
    payload = build_signal_slack_payload(signal)
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Alert Log — persistent history
# ---------------------------------------------------------------------------

def save_alert_log(alerts: List[Alert]) -> None:
    HASH_STORE_DIR.mkdir(parents=True, exist_ok=True)
    history: List[Dict[str, Any]] = []
    if ALERT_LOG_FILE.exists():
        try:
            with open(ALERT_LOG_FILE, encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    now = datetime.now(timezone.utc).isoformat()
    for a in alerts:
        history.append({"timestamp": now, **asdict(a)})

    # Keep last 500 alerts
    history = history[-500:]

    try:
        with open(ALERT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save alert log: {e}")


# ---------------------------------------------------------------------------
# Main Monitor Loop
# ---------------------------------------------------------------------------

def run_monitor(
    dry_run: bool = False,
    profile: str = RunProfile.PRIORITY.value,
) -> Dict[str, Any]:
    """Execute one monitoring cycle."""
    selected_entries = select_sources(ALL_URLS, profile=profile)
    summary_by_priority = classification_summary(selected_entries)
    run_owner_id = f"run_{uuid4().hex[:10]}"
    run_lock_store = RunLockStore()
    lock_acquired = run_lock_store.acquire(
        lock_name=MONITOR_RUN_LOCK_NAME,
        owner_id=run_owner_id,
        ttl_seconds=MONITOR_RUN_LOCK_TTL_SECONDS,
    )
    if not lock_acquired:
        logger.warning(
            "Monitor run skipped: lock '%s' is already held by another process",
            MONITOR_RUN_LOCK_NAME,
        )
        return {
            "total": 0,
            "ok": 0,
            "changed": 0,
            "new": 0,
            "blocked": 0,
            "errors": 0,
            "noise": 0,
            "signals": 0,
            "duration_s": 0.0,
            "profile": profile,
            "selected": len(selected_entries),
            "skipped": "lock_unavailable",
        }

    logger.info("=" * 60)
    logger.info("AEGIS Regulatory Monitor — starting cycle")
    logger.info(
        "Monitoring profile=%s | selected=%d/%d URLs "
        "(critical=%d active=%d sweep=%d)",
        profile,
        len(selected_entries),
        len(ALL_URLS),
        summary_by_priority.get("critical", 0),
        summary_by_priority.get("active", 0),
        summary_by_priority.get("sweep", 0),
    )
    logger.info(f"Hash store: {HASH_STORE_FILE}")
    logger.info(f"Slack webhook: {'configured' if SLACK_WEBHOOK_URL else 'NOT configured'}")
    if dry_run:
        logger.info("*** DRY RUN — no state saved, no alerts sent ***")
    logger.info("=" * 60)

    cycle_start = time.monotonic()
    store = load_hash_store()
    is_first_run = len(store) == 0
    snapshot_store = SnapshotStore()
    signal_store = SignalStore()
    signal_analyzer = SignalAnalyzer()
    impact_assessor = ImpactAssessor()

    alerts: List[Alert] = []
    intelligence_signals: List[RegulatorySignal] = []
    counts = {
        "total": 0,
        "ok": 0,
        "changed": 0,
        "new": 0,
        "blocked": 0,
        "errors": 0,
        "noise": 0,
        "signals": 0,
    }

    for entry in selected_entries:
        counts["total"] += 1
        url = entry.url

        cls = classify_source(entry)
        logger.info(
            f"[{counts['total']:2d}/{len(selected_entries)}] {entry.label} "
            f"[{cls.priority}/{cls.cadence}]"
        )

        result = fetch_url(entry)
        logger.info(f"  {result.status.value} | {result.elapsed_ms}ms | {result.content_length} bytes")

        now_iso = datetime.now(timezone.utc).isoformat()
        previous = store.get(url)
        status_transition: Optional[str] = None
        if previous and previous.status not in {"ok", "changed", "new"}:
            status_transition = f"{previous.status}_to_200"

        if result.status == URLStatus.OK:
            assert result.content_hash is not None

            source_id = source_id_for_url(url)
            previous_snapshot = snapshot_store.load_latest(source_id)

            extracted = extract_text(
                result.raw_content,
                url=url,
                content_type=result.content_type,
            )
            normalized_text, rules_applied = normalize_text(extracted.text)
            normalized_hash = normalized_content_hash(normalized_text)
            current_snapshot = ContentSnapshot(
                source_id=source_id,
                url=url,
                label=entry.label,
                country=entry.country,
                tier=entry.tier.value,
                raw_hash=result.content_hash,
                content_hash=normalized_hash,
                extracted_text=normalized_text,
                captured_at=now_iso,
                content_length=result.content_length,
                extraction_method=extracted.extraction_method,
                content_type=result.content_type,
                http_status=result.http_status or 200,
                headers=result.response_headers,
                normalization_rules_applied=rules_applied,
            )
            if not dry_run:
                snapshot_store.save(current_snapshot, raw_content=result.raw_content)

            content_diff = generate_diff(
                previous=previous_snapshot,
                current=current_snapshot,
                keyword_hits=[],
            )
            content_diff.keyword_hits = find_keyword_hits(content_diff)

            if previous is None:
                counts["new"] += 1
                store[url] = URLHashRecord(
                    url=url, hash=result.content_hash,
                    last_checked=now_iso, last_changed=now_iso,
                    status="new", content_length=result.content_length,
                    check_count=1, change_count=0,
                )
                if not is_first_run:
                    logger.info(f"  → NEW URL added to monitoring")
                    status_transition = "new_url"

            elif result.content_hash != previous.hash:
                if content_diff.noise_filtered:
                    counts["noise"] += 1
                    logger.info("  → RAW changed but normalized content unchanged (noise)")
                    store[url] = URLHashRecord(
                        url=url, hash=result.content_hash,
                        last_checked=now_iso, last_changed=previous.last_changed,
                        status="ok", content_length=result.content_length,
                        check_count=previous.check_count + 1,
                        change_count=previous.change_count,
                    )
                else:
                    counts["changed"] += 1
                    logger.warning(f"  → CHANGED! {previous.hash[:16]}… → {result.content_hash[:16]}…")
                    alerts.append(Alert(
                        url=url, label=entry.label, country=entry.country,
                        tier=entry.tier.value, status="changed",
                        detail=(
                            f"Raw hash changed; {content_diff.summary}. "
                            f"Keywords: {', '.join(content_diff.keyword_hits[:3]) if content_diff.keyword_hits else 'none'}"
                        ),
                        old_hash=previous.hash, new_hash=result.content_hash,
                    ))
                    store[url] = URLHashRecord(
                        url=url, hash=result.content_hash,
                        last_checked=now_iso, last_changed=now_iso,
                        status="changed", content_length=result.content_length,
                        check_count=previous.check_count + 1,
                        change_count=previous.change_count + 1,
                    )
            else:
                counts["ok"] += 1
                store[url] = URLHashRecord(
                    url=url, hash=previous.hash,
                    last_checked=now_iso, last_changed=previous.last_changed,
                    status="ok", content_length=result.content_length,
                    check_count=previous.check_count + 1,
                    change_count=previous.change_count,
                )

            trigger = evaluate_trigger(
                diff=content_diff,
                tier=entry.tier.value,
                is_new_url=(previous is None and not is_first_run),
                status_transition=status_transition,
            )
            if trigger.trigger_level3 and not is_first_run:
                triage = signal_analyzer.analyze(content_diff, tier=entry.tier.value)
                signal = RegulatorySignal(
                    signal_id=f"sig_{uuid4().hex[:12]}",
                    source_url=url,
                    source_label=entry.label,
                    country=entry.country,
                    detected_at=now_iso,
                    classification=triage.classification,
                    severity=triage.signal_severity,
                    summary=triage.summary or content_diff.summary,
                    compounds_affected=triage.compounds_affected,
                    jurisdictions_affected=triage.jurisdictions_affected or [entry.country],
                    action_type=triage.action_type,
                    effective_date=triage.effective_date,
                    confidence=triage.confidence,
                    raw_signal=triage.raw_signal,
                    diff_id=content_diff.diff_id,
                    triage=dataclass_to_plain(triage),
                    fetch_provenance=result.fetched_via,
                )

                if triage.signal_severity in {"critical", "high", "medium"} or trigger.alert_immediately:
                    impact = impact_assessor.assess(signal)
                    signal.impact = dataclass_to_plain(impact)
                    signal.priority_score = float(impact.score_components.get("priority_score", 0.0))

                counts["signals"] += 1
                intelligence_signals.append(signal)
                if not dry_run:
                    signal_store.append(signal)

        elif result.status == URLStatus.BLOCKED:
            counts["blocked"] += 1
            if not entry.known_blocked:
                alerts.append(Alert(
                    url=url, label=entry.label, country=entry.country,
                    tier=entry.tier.value, status="blocked",
                    detail=result.error or "Access blocked",
                ))
            else:
                logger.info(f"  → Known blocked (expected)")

            if previous:
                store[url] = URLHashRecord(
                    url=url, hash=previous.hash,
                    last_checked=now_iso, last_changed=previous.last_changed,
                    status="blocked", content_length=0,
                    check_count=previous.check_count + 1,
                    change_count=previous.change_count,
                )
            else:
                store[url] = URLHashRecord(
                    url=url, hash="", last_checked=now_iso,
                    last_changed=None, status="blocked",
                    content_length=0, check_count=1, change_count=0,
                )

        elif result.status in (URLStatus.NOT_FOUND, URLStatus.DEGRADED, URLStatus.SSL_ERROR):
            counts["errors"] += 1
            alerts.append(Alert(
                url=url, label=entry.label, country=entry.country,
                tier=entry.tier.value, status=result.status.value,
                detail=result.error or f"HTTP {result.http_status}",
            ))
            if previous and previous.status in {"ok", "changed", "new"} and result.status == URLStatus.NOT_FOUND:
                status_signal = RegulatorySignal(
                    signal_id=f"sig_{uuid4().hex[:12]}",
                    source_url=url,
                    source_label=entry.label,
                    country=entry.country,
                    detected_at=now_iso,
                    classification="data_update",
                    severity="high",
                    summary="Monitored page changed state from HTTP 200 to HTTP 404.",
                    compounds_affected=[],
                    jurisdictions_affected=[entry.country],
                    action_type="page_removed",
                    effective_date=None,
                    confidence=0.99,
                    raw_signal=result.error or "404 Not Found",
                    diff_id=f"status_{uuid4().hex[:10]}",
                    triage={"classification": "data_update", "signal_severity": "high", "model_used": "system"},
                    fetch_provenance="system",
                )
                impact = impact_assessor.assess(status_signal)
                status_signal.impact = dataclass_to_plain(impact)
                status_signal.priority_score = float(impact.score_components.get("priority_score", 0.0))
                counts["signals"] += 1
                intelligence_signals.append(status_signal)
                if not dry_run:
                    signal_store.append(status_signal)

            if previous:
                store[url] = URLHashRecord(
                    url=url, hash=previous.hash,
                    last_checked=now_iso, last_changed=previous.last_changed,
                    status=result.status.value, content_length=0,
                    check_count=previous.check_count + 1,
                    change_count=previous.change_count,
                )
            else:
                store[url] = URLHashRecord(
                    url=url, hash="", last_checked=now_iso,
                    last_changed=None, status=result.status.value,
                    content_length=0, check_count=1, change_count=0,
                )

        else:
            counts["errors"] += 1
            logger.warning(f"  → {result.status.value}: {result.error}")
            if previous:
                store[url] = URLHashRecord(
                    url=url, hash=previous.hash,
                    last_checked=now_iso, last_changed=previous.last_changed,
                    status=result.status.value, content_length=0,
                    check_count=previous.check_count + 1,
                    change_count=previous.change_count,
                )
            else:
                store[url] = URLHashRecord(
                    url=url, hash="", last_checked=now_iso,
                    last_changed=None, status=result.status.value,
                    content_length=0, check_count=1, change_count=0,
                )

        # Rate limiting
        time.sleep(REQUEST_DELAY_SECONDS)

    duration = time.monotonic() - cycle_start
    counts["duration_s"] = duration

    logger.info("=" * 60)
    logger.info(f"Cycle complete in {duration:.1f}s")
    logger.info(f"  OK: {counts['ok']}  Changed: {counts['changed']}  "
                f"New: {counts['new']}  Noise: {counts['noise']}  "
                f"Blocked: {counts['blocked']}  Errors: {counts['errors']}")
    logger.info(f"  Alerts: {len(alerts)}  Signals: {counts['signals']}")
    logger.info("=" * 60)

    # Save state
    if not dry_run:
        save_hash_store(store)
        if alerts:
            send_slack_alert(alerts, counts)
            save_alert_log(alerts)
        for signal in intelligence_signals:
            route = route_for_impact((signal.impact or {}).get("impact_rating", "none") if signal.impact else "none")
            if route in {"critical", "high"}:
                delivered = send_intelligence_signal_alert(signal)
                if not delivered:
                    fallback = dispatch_critical_fallback(signal, reason="slack_delivery_failed")
                    logger.error(
                        "Critical alert fallback invoked for %s | email=%s pagerduty=%s",
                        signal.signal_id,
                        fallback.get("email_sent"),
                        fallback.get("pagerduty_sent"),
                    )
    else:
        logger.info("[DRY RUN] State NOT saved. Alerts NOT sent.")
        if alerts:
            logger.info(f"[DRY RUN] Would have sent {len(alerts)} alert(s):")
            for a in alerts:
                logger.info(f"  [{a.status:10s}] {a.country:12s} | {a.label}")
        if intelligence_signals:
            logger.info(f"[DRY RUN] Would have generated {len(intelligence_signals)} intelligence signal(s)")

    # First-run init notification
    if is_first_run and not dry_run and SLACK_WEBHOOK_URL:
        try:
            requests.post(SLACK_WEBHOOK_URL, json={
                "text": (
                    "✅ AEGIS Regulatory Monitor initialized — "
                    f"profile={profile}, tracking {len(selected_entries)} URLs "
                    f"across {len(set(e.country for e in selected_entries))} jurisdictions."
                )
            }, timeout=10)
        except Exception:
            pass

    try:
        run_lock_store.release(lock_name=MONITOR_RUN_LOCK_NAME, owner_id=run_owner_id)
    except Exception as exc:
        logger.error("Failed releasing run lock '%s': %s", MONITOR_RUN_LOCK_NAME, exc)

    counts["profile"] = profile
    counts["selected"] = len(selected_entries)
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AEGIS Regulatory URL Monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check URLs but don't save state or send alerts")
    parser.add_argument(
        "--profile",
        choices=[
            RunProfile.CRITICAL.value,
            RunProfile.ACTIVE.value,
            RunProfile.PRIORITY.value,
            RunProfile.FULL.value,
            RunProfile.SWEEP.value,
        ],
        default=RunProfile.PRIORITY.value,
        help="Source run profile (default: priority = critical+active)",
    )
    parser.add_argument("--list", action="store_true",
                        help="List all monitored URLs and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show current hash store status and exit")
    args = parser.parse_args()

    if args.list:
        print(f"\nAEGIS Monitored URLs ({len(ALL_URLS)} total)")
        print("=" * 90)
        for i, entry in enumerate(ALL_URLS, 1):
            blocked = " [KNOWN BLOCKED]" if entry.known_blocked else ""
            cls = classify_source(entry)
            print(
                f"{i:3d}. [{entry.tier.value:9s}] [{entry.country:14s}] "
                f"[{cls.priority:8s}/{cls.cadence:7s}] {entry.label}{blocked}"
            )
            print(f"     {entry.url}")
        print("\nProfile Selection Totals")
        print("-" * 90)
        for profile in [
            RunProfile.CRITICAL.value,
            RunProfile.ACTIVE.value,
            RunProfile.PRIORITY.value,
            RunProfile.SWEEP.value,
            RunProfile.FULL.value,
        ]:
            selected = select_sources(ALL_URLS, profile=profile)
            counts = classification_summary(selected)
            print(
                f"{profile:9s}: {len(selected):2d} URLs "
                f"(critical={counts.get('critical',0)}, active={counts.get('active',0)}, sweep={counts.get('sweep',0)})"
            )
        return

    if args.status:
        store = load_hash_store()
        if not store:
            print("No hash store found — monitor has not run yet.")
            return
        print(f"\nAEGIS Monitor Status ({len(store)} URLs tracked)")
        print("=" * 90)
        for url, rec in sorted(store.items(), key=lambda x: x[1].last_checked, reverse=True):
            emoji = {"ok": "✅", "changed": "🔔", "new": "🆕", "blocked": "🚫",
                     "not_found": "❌", "degraded": "🟡", "ssl_error": "🔴",
                     "failed": "⚠️"}.get(rec.status, "❓")
            print(f"{emoji} [{rec.status:10s}] checks={rec.check_count:3d}  changes={rec.change_count:2d}  last={rec.last_checked[:19]}")
            print(f"   {url[:85]}")
        return

    counts = run_monitor(dry_run=args.dry_run, profile=args.profile)

    if counts.get("changed", 0) > 0 or counts.get("errors", 0) > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
