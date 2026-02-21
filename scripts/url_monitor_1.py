#!/usr/bin/env python3
"""
Module: url_monitor
Purpose: Daily regulatory URL change detection for AEGIS.
    Fetches monitored government and aggregator pages worldwide,
    hashes content, compares against stored state, and alerts via
    Slack webhook when changes are detected.

    Designed to run as a Railway cron worker (0 6 * * * UTC).

    Coverage: US, EU, International, Canada, APAC (7 countries)
    Total monitored URLs: ~55

    Rev History:
        1.0.0 - Initial APAC-only monitor (26 URLs)
        2.0.0 - Worldwide coverage matching full regulatory framework

BoundState AI 2026
Version: 2.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Co-Authored-By: Claude Opus 4.6 (Beth) <noreply@anthropic.com>
"""

from __future__ import annotations

import hashlib
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

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("aegis.monitor")

HASH_STORE_DIR = Path(os.getenv("MONITOR_STORE_DIR", "./monitor_data"))
HASH_STORE_FILE = HASH_STORE_DIR / "url_hashes.json"
ALERT_LOG_FILE = HASH_STORE_DIR / "alert_history.json"

SLACK_WEBHOOK_URL = os.getenv("MONITOR_SLACK_WEBHOOK", "")

REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
USER_AGENT = "BoundState-AEGIS-Monitor/2.0 (regulatory-change-detection; contact@boundstate.ai)"
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


# ===================================================================
# UNITED STATES — EPA, TSCA, CERCLA, State-level
# ===================================================================
US_URLS: List[MonitoredURL] = [
    # EPA PFAS portal + SDWA
    MonitoredURL(
        url="https://www.epa.gov/pfas",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — PFAS Strategic Roadmap portal",
    ),
    MonitoredURL(
        url="https://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — SDWA PFAS drinking water regulation",
    ),
    MonitoredURL(
        url="https://www.epa.gov/system/files/documents/2024-04/pfas-npdwr_final-rule.pdf",
        tier=URLTier.DOCUMENT, country="US",
        label="EPA — PFAS NPDWR Final Rule (PDF)",
    ),
    # CERCLA / Superfund
    MonitoredURL(
        url="https://www.epa.gov/superfund/proposed-designation-perfluorooctanoic-acid-pfoa-and-perfluorooctanesulfonic-acid-pfos",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — CERCLA PFOA/PFOS hazardous substance designation",
    ),
    # TSCA
    MonitoredURL(
        url="https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/pfas-under-tsca",
        tier=URLTier.PRIMARY, country="US",
        label="EPA — PFAS under TSCA",
    ),
    # CompTox dashboard (data source for our EPA database)
    MonitoredURL(
        url="https://comptox.epa.gov/dashboard/chemical-lists/PFASMASTER",
        tier=URLTier.PRIMARY, country="US",
        label="EPA CompTox — PFAS Master List",
    ),
    # California Prop 65
    MonitoredURL(
        url="https://oehha.ca.gov/proposition-65/chemicals/pfoa-perfluorooctanoic-acid",
        tier=URLTier.PRIMARY, country="US-CA",
        label="CA OEHHA — Prop 65 PFOA listing",
    ),
    MonitoredURL(
        url="https://oehha.ca.gov/proposition-65/chemicals/pfos-perfluorooctane-sulfonic-acid-and-its-salts",
        tier=URLTier.PRIMARY, country="US-CA",
        label="CA OEHHA — Prop 65 PFOS listing",
    ),
    # State PFAS legislation tracker (NCEL — clean aggregator)
    MonitoredURL(
        url="https://www.ncel.net/pfas/",
        tier=URLTier.SECONDARY, country="US",
        label="NCEL — State PFAS legislation tracker",
    ),
]

# ===================================================================
# EUROPEAN UNION — ECHA, REACH, POPs Regulation
# ===================================================================
EU_URLS: List[MonitoredURL] = [
    # ECHA PFAS restriction proposal (the big one)
    MonitoredURL(
        url="https://echa.europa.eu/restrictions-under-consideration/-/substance-rev/72301/term",
        tier=URLTier.PRIMARY, country="EU",
        label="ECHA — Universal PFAS restriction proposal",
    ),
    # ECHA PFAS registry
    MonitoredURL(
        url="https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas",
        tier=URLTier.PRIMARY, country="EU",
        label="ECHA — PFAS hot topics portal",
    ),
    # EU POPs Regulation
    MonitoredURL(
        url="https://environment.ec.europa.eu/topics/chemicals/persistent-organic-pollutants-pops_en",
        tier=URLTier.PRIMARY, country="EU",
        label="EC — Persistent Organic Pollutants (POPs) Regulation",
    ),
    # REACH substance registry — PFOA
    MonitoredURL(
        url="https://echa.europa.eu/substance-information/-/substanceinfo/100.004.808",
        tier=URLTier.PRIMARY, country="EU",
        label="ECHA — PFOA substance information",
    ),
    # Fluoropolymers Europe (industry response / derogation tracker)
    MonitoredURL(
        url="https://fluoropolymers.eu/eu-pfas-restriction/",
        tier=URLTier.SECONDARY, country="EU",
        label="Fluoropolymers Europe — PFAS restriction analysis",
    ),
]

# ===================================================================
# INTERNATIONAL — Stockholm Convention, OECD
# ===================================================================
INTL_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="http://chm.pops.int/Implementation/NationalImplementationPlans/NIPTransmission/tabid/253/Default.aspx",
        tier=URLTier.PRIMARY, country="International",
        label="Stockholm Convention — National Implementation Plans",
    ),
    MonitoredURL(
        url="https://www.oecd.org/chemicalsafety/portal-perfluorinated-chemicals/",
        tier=URLTier.PRIMARY, country="International",
        label="OECD — PFAS Portal",
    ),
]

# ===================================================================
# CANADA
# ===================================================================
CANADA_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://www.canada.ca/en/health-canada/services/chemical-substances/other-chemical-substances-interest/per-polyfluoroalkyl-substances.html",
        tier=URLTier.PRIMARY, country="Canada",
        label="Health Canada — PFAS overview",
    ),
    MonitoredURL(
        url="https://www.canada.ca/en/environment-climate-change/services/evaluating-existing-substances/screening-assessment-pfas.html",
        tier=URLTier.PRIMARY, country="Canada",
        label="ECCC — PFAS screening assessment",
    ),
]

# ===================================================================
# JAPAN
# ===================================================================
JAPAN_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://www.nite.go.jp/chem/english/kasinn/index.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="NITE J-CHECK — Class I Chemical Substances",
    ),
    MonitoredURL(
        url="https://www.meti.go.jp/policy/chemical_management/kasinhou/todoke/1rui_tokuteikagaku.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="METI — Class I Specified Chemical Substances list",
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
        url="https://www.meti.go.jp/english/press/2024/0705_002.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="METI — PFOA Cabinet Order July 2024",
    ),
    MonitoredURL(
        url="https://www.meti.go.jp/english/press/2023/1128_002.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="METI — PFHxS Cabinet Order Nov 2023",
    ),
    MonitoredURL(
        url="https://www.meti.go.jp/english/press/2025/1212_001.html",
        tier=URLTier.PRIMARY, country="Japan",
        label="METI — PFHxS-related compounds Dec 2025",
    ),
]

# ===================================================================
# SOUTH KOREA
# ===================================================================
KOREA_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://www.me.go.kr/eng/web/main.do",
        tier=URLTier.PRIMARY, country="South Korea",
        label="Korea MOE — Ministry of Environment English portal",
    ),
    MonitoredURL(
        url="https://www.mfds.go.kr/eng/wpge/m_24/de011014l001.do",
        tier=URLTier.PRIMARY, country="South Korea",
        label="Korea MFDS — Cosmetics Safety Standards",
    ),
]

# ===================================================================
# CHINA
# ===================================================================
CHINA_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://www.mee.gov.cn/",
        tier=URLTier.PRIMARY, country="China",
        label="China MEE — Ministry of Ecology and Environment portal",
    ),
]

# ===================================================================
# AUSTRALIA
# ===================================================================
AUSTRALIA_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://www.nhmrc.gov.au/about-us/news-centre/updated-australian-drinking-water-guidelines",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC — Australian Drinking Water Guidelines update",
        known_blocked=True,
    ),
    MonitoredURL(
        url="https://www.nhmrc.gov.au/health-advice/environmental-health/water/PFAS-review",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC — PFAS in Drinking Water review",
        known_blocked=True,
    ),
    MonitoredURL(
        url="https://guidelines.nhmrc.gov.au/australian-drinking-water-guidelines/part-5/physical-chemical-characteristics/cas-numbers-1763-23-1-pfos-335-67-1-pfoa-355-46-4-pfhxs",
        tier=URLTier.PRIMARY, country="Australia",
        label="NHMRC ADWG — PFAS guideline values (PFOS/PFOA/PFHxS)",
    ),
    MonitoredURL(
        url="https://www.dcceew.gov.au/environment/protection/chemicals-management/pfas",
        tier=URLTier.PRIMARY, country="Australia",
        label="DCCEEW — PFAS management landing page",
        known_blocked=True,
    ),
    MonitoredURL(
        url="https://www.dcceew.gov.au/environment/protection/publications/pfas-nemp-3",
        tier=URLTier.PRIMARY, country="Australia",
        label="DCCEEW — PFAS NEMP 3.0 publication",
        known_blocked=True,
    ),
]

# ===================================================================
# SINGAPORE
# ===================================================================
SINGAPORE_URLS: List[MonitoredURL] = [
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
]

# ===================================================================
# TAIWAN
# ===================================================================
TAIWAN_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://www.cha.gov.tw/fp-193-6212-09aa4-2.html",
        tier=URLTier.PRIMARY, country="Taiwan",
        label="Taiwan Chemicals Administration — PFHxS designation",
    ),
]

# ===================================================================
# INDIA
# ===================================================================
INDIA_URLS: List[MonitoredURL] = [
    MonitoredURL(
        url="https://cpcb.nic.in/",
        tier=URLTier.PRIMARY, country="India",
        label="India CPCB — Central Pollution Control Board portal",
    ),
]

# ===================================================================
# SECONDARY AGGREGATORS — worldwide regulatory news
# ===================================================================
SECONDARY_URLS: List[MonitoredURL] = [
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
        url="https://en.reach24h.com/news/industry-news/chemical/",
        tier=URLTier.SECONDARY, country="China",
        label="REACH24H — China chemical regulatory news",
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
    MonitoredURL(
        url="https://chemicalwatch.com/pfas",
        tier=URLTier.SECONDARY, country="Global",
        label="Chemical Watch — Global PFAS regulatory tracker",
    ),
]

# Build complete list by region
ALL_URLS = (
    US_URLS
    + EU_URLS
    + INTL_URLS
    + CANADA_URLS
    + JAPAN_URLS
    + KOREA_URLS
    + CHINA_URLS
    + AUSTRALIA_URLS
    + SINGAPORE_URLS
    + TAIWAN_URLS
    + INDIA_URLS
    + SECONDARY_URLS
)

# Region summary for logging
REGION_COUNTS = {
    "US": len(US_URLS),
    "EU": len(EU_URLS),
    "International": len(INTL_URLS),
    "Canada": len(CANADA_URLS),
    "Japan": len(JAPAN_URLS),
    "South Korea": len(KOREA_URLS),
    "China": len(CHINA_URLS),
    "Australia": len(AUSTRALIA_URLS),
    "Singapore": len(SINGAPORE_URLS),
    "Taiwan": len(TAIWAN_URLS),
    "India": len(INDIA_URLS),
    "Secondary": len(SECONDARY_URLS),
}


# ---------------------------------------------------------------------------
# Hash Store
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
            raw = json.load(f)
        store = {}
        for url, data in raw.items():
            store[url] = URLHashRecord(
                url=data["url"], hash=data["hash"],
                last_checked=data["last_checked"],
                last_changed=data.get("last_changed"),
                status=data.get("status", "ok"),
                content_length=data.get("content_length", 0),
                check_count=data.get("check_count", 0),
                change_count=data.get("change_count", 0),
            )
        logger.info(f"Loaded hash store: {len(store)} URLs tracked")
        return store
    except Exception as e:
        logger.error(f"Failed to load hash store: {e}")
        return {}


def save_hash_store(store: Dict[str, URLHashRecord]) -> None:
    HASH_STORE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        raw = {url: asdict(record) for url, record in store.items()}
        with open(HASH_STORE_FILE, "w", encoding="utf-8") as f:
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
    error: Optional[str] = None
    http_status: Optional[int] = None
    elapsed_ms: int = 0


def fetch_url(entry: MonitoredURL) -> FetchResult:
    url = entry.url
    headers = {"User-Agent": USER_AGENT}
    start = time.monotonic()

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, headers=headers,
                timeout=REQUEST_TIMEOUT, allow_redirects=True,
            )
            elapsed = int((time.monotonic() - start) * 1000)

            if resp.status_code == 403:
                return FetchResult(url=url, status=URLStatus.BLOCKED,
                    error="403 Forbidden", http_status=403, elapsed_ms=elapsed)
            elif resp.status_code == 404:
                return FetchResult(url=url, status=URLStatus.NOT_FOUND,
                    error="404 Not Found — URL may have moved",
                    http_status=404, elapsed_ms=elapsed)
            elif resp.status_code >= 500:
                if attempt < MAX_RETRIES:
                    logger.warning(f"  Retry {attempt+1}/{MAX_RETRIES} for {url} (HTTP {resp.status_code})")
                    time.sleep(2)
                    continue
                return FetchResult(url=url, status=URLStatus.DEGRADED,
                    error=f"HTTP {resp.status_code} after {MAX_RETRIES+1} attempts",
                    http_status=resp.status_code, elapsed_ms=elapsed)
            elif resp.status_code != 200:
                return FetchResult(url=url, status=URLStatus.FAILED,
                    error=f"HTTP {resp.status_code}",
                    http_status=resp.status_code, elapsed_ms=elapsed)

            content_hash = hashlib.sha256(resp.content).hexdigest()
            return FetchResult(url=url, status=URLStatus.OK,
                content_hash=content_hash, content_length=len(resp.content),
                http_status=200, elapsed_ms=elapsed)

        except requests.exceptions.SSLError as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(url=url, status=URLStatus.SSL_ERROR,
                error=str(e)[:200], elapsed_ms=elapsed)
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                logger.warning(f"  Timeout retry {attempt+1}/{MAX_RETRIES} for {url}")
                continue
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(url=url, status=URLStatus.TIMEOUT,
                error=f"Timeout after {REQUEST_TIMEOUT}s x {MAX_RETRIES+1} attempts",
                elapsed_ms=elapsed)
        except requests.exceptions.ConnectionError as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"  Connection retry {attempt+1}/{MAX_RETRIES} for {url}")
                time.sleep(2)
                continue
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(url=url, status=URLStatus.FAILED,
                error=f"Connection failed: {str(e)[:200]}", elapsed_ms=elapsed)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return FetchResult(url=url, status=URLStatus.FAILED,
                error=f"Unexpected: {str(e)[:200]}", elapsed_ms=elapsed)

    return FetchResult(url=url, status=URLStatus.FAILED, error="Exhausted retries")


# ---------------------------------------------------------------------------
# Alert Engine
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
                "text": {"type": "mrkdwn", "text": f"{emoji} *{a.label}* ({a.country}) — {a.status}\n{a.detail}"},
            })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": (
            f"Checked {summary['total']} URLs | "
            f"OK: {summary['ok']} | Changed: {summary['changed']} | "
            f"New: {summary['new']} | Blocked: {summary['blocked']} | "
            f"Errors: {summary['errors']} | Duration: {summary['duration_s']:.1f}s"
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
    history = history[-500:]

    try:
        with open(ALERT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save alert log: {e}")


# ---------------------------------------------------------------------------
# Main Monitor Loop
# ---------------------------------------------------------------------------

def run_monitor(dry_run: bool = False) -> Dict[str, Any]:
    """Execute one worldwide monitoring cycle."""
    logger.info("=" * 70)
    logger.info("AEGIS Regulatory Monitor v2.0 — Worldwide Coverage")
    logger.info(f"Total URLs: {len(ALL_URLS)}")
    for region, count in REGION_COUNTS.items():
        logger.info(f"  {region:15s}: {count}")
    logger.info(f"Hash store: {HASH_STORE_FILE}")
    logger.info(f"Slack: {'configured' if SLACK_WEBHOOK_URL else 'NOT configured'}")
    if dry_run:
        logger.info("*** DRY RUN — no state saved, no alerts sent ***")
    logger.info("=" * 70)

    cycle_start = time.monotonic()
    store = load_hash_store()
    is_first_run = len(store) == 0

    alerts: List[Alert] = []
    counts = {"total": 0, "ok": 0, "changed": 0, "new": 0, "blocked": 0, "errors": 0}

    for entry in ALL_URLS:
        counts["total"] += 1
        url = entry.url

        logger.info(f"[{counts['total']:2d}/{len(ALL_URLS)}] [{entry.country:14s}] {entry.label}")

        result = fetch_url(entry)
        logger.info(f"  {result.status.value} | {result.elapsed_ms}ms | {result.content_length} bytes")

        now_iso = datetime.now(timezone.utc).isoformat()
        previous = store.get(url)

        if result.status == URLStatus.OK:
            assert result.content_hash is not None

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

            elif result.content_hash != previous.hash:
                counts["changed"] += 1
                logger.warning(f"  → CHANGED! {previous.hash[:16]}… → {result.content_hash[:16]}…")
                alerts.append(Alert(
                    url=url, label=entry.label, country=entry.country,
                    tier=entry.tier.value, status="changed",
                    detail=f"Content hash changed ({result.content_length} bytes)",
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

        time.sleep(REQUEST_DELAY_SECONDS)

    duration = time.monotonic() - cycle_start
    counts["duration_s"] = duration

    logger.info("=" * 70)
    logger.info(f"Cycle complete in {duration:.1f}s")
    logger.info(f"  OK: {counts['ok']}  Changed: {counts['changed']}  "
                f"New: {counts['new']}  Blocked: {counts['blocked']}  Errors: {counts['errors']}")
    logger.info(f"  Alerts: {len(alerts)}")
    logger.info("=" * 70)

    if not dry_run:
        save_hash_store(store)
        if alerts:
            send_slack_alert(alerts, counts)
            save_alert_log(alerts)
    else:
        logger.info("[DRY RUN] State NOT saved. Alerts NOT sent.")
        if alerts:
            logger.info(f"[DRY RUN] Would have sent {len(alerts)} alert(s):")
            for a in alerts:
                logger.info(f"  [{a.status:10s}] {a.country:14s} | {a.label}")

    if is_first_run and not dry_run and SLACK_WEBHOOK_URL:
        try:
            regions = len(set(e.country for e in ALL_URLS))
            requests.post(SLACK_WEBHOOK_URL, json={
                "text": f"✅ AEGIS Regulatory Monitor v2.0 initialized — tracking {len(ALL_URLS)} URLs across {regions} jurisdictions worldwide."
            }, timeout=10)
        except Exception:
            pass

    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AEGIS Regulatory URL Monitor v2.0 — Worldwide")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check URLs but don't save state or send alerts")
    parser.add_argument("--list", action="store_true",
                        help="List all monitored URLs and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show current hash store status and exit")
    parser.add_argument("--region", type=str, default=None,
                        help="Only check URLs for a specific country/region (e.g., 'US', 'Japan', 'EU')")
    args = parser.parse_args()

    if args.list:
        print(f"\nAEGIS Monitored URLs v2.0 ({len(ALL_URLS)} total)")
        print("=" * 95)
        for region, count in REGION_COUNTS.items():
            print(f"  {region}: {count}")
        print("=" * 95)
        current_country = None
        for i, entry in enumerate(ALL_URLS, 1):
            if entry.country != current_country:
                current_country = entry.country
                print(f"\n  --- {current_country} ---")
            blocked = " [KNOWN BLOCKED]" if entry.known_blocked else ""
            print(f"  {i:3d}. [{entry.tier.value:9s}] {entry.label}{blocked}")
            print(f"       {entry.url}")
        return

    if args.status:
        store = load_hash_store()
        if not store:
            print("No hash store found — monitor has not run yet.")
            return
        print(f"\nAEGIS Monitor Status ({len(store)} URLs tracked)")
        print("=" * 95)
        for url, rec in sorted(store.items(), key=lambda x: x[1].last_checked, reverse=True):
            emoji = {"ok": "✅", "changed": "🔔", "new": "🆕", "blocked": "🚫",
                     "not_found": "❌", "degraded": "🟡", "ssl_error": "🔴",
                     "failed": "⚠️"}.get(rec.status, "❓")
            print(f"{emoji} [{rec.status:10s}] checks={rec.check_count:3d}  changes={rec.change_count:2d}  last={rec.last_checked[:19]}")
            print(f"   {url[:90]}")
        return

    # Region filter
    if args.region:
        global ALL_URLS
        region_lower = args.region.lower()
        ALL_URLS = [e for e in ALL_URLS if e.country.lower().startswith(region_lower)]
        if not ALL_URLS:
            print(f"No URLs found for region '{args.region}'. Use --list to see available regions.")
            sys.exit(1)
        logger.info(f"Filtered to {len(ALL_URLS)} URLs for region '{args.region}'")

    counts = run_monitor(dry_run=args.dry_run)

    if counts.get("changed", 0) > 0 or counts.get("errors", 0) > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
