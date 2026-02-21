#!/usr/bin/env python3
"""
Chemours-priority source classification for monitor run profiles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Protocol


class URLSource(Protocol):
    url: str
    label: str
    country: str
    tier: object


class SourcePriority(str, Enum):
    CRITICAL = "critical"   # Daily, board-level / legal exposure
    ACTIVE = "active"       # Weekly, important but not immediate
    SWEEP = "sweep"         # Monthly sweep / long-tail watchlist


class RunProfile(str, Enum):
    CRITICAL = "critical"   # only critical sources
    ACTIVE = "active"       # only active sources
    PRIORITY = "priority"   # critical + active (default)
    FULL = "full"           # all 62
    SWEEP = "sweep"         # monthly sweep only


@dataclass(frozen=True)
class SourceClassification:
    url: str
    label: str
    country: str
    tier: str
    priority: str
    cadence: str
    rationale: str


CRITICAL_URLS = {
    # US federal/state litigation/regulatory drivers
    "https://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas",
    "https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping",
    "https://www.epa.gov/superfund/questions-and-answers-about-designation-pfoa-and-pfos-hazardous-substances-under-cercla",
    "https://www.govinfo.gov/content/pkg/FR-2024-04-26/pdf/2024-07773.pdf",
    "https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=environmental-protection-agency&conditions%5Bterm%5D=PFAS&order=newest",
    "https://deq.nc.gov/news/key-issues/genx-investigation",
    "https://www.waterboards.ca.gov/drinking_water/certlic/drinkingwater/pfas.html",
    "https://oehha.ca.gov/proposition-65/chemicals/perfluorooctanoic-acid-pfoa",
    "https://oehha.ca.gov/proposition-65/chemicals/perfluorooctane-sulfonate-pfos",
    "https://ecology.wa.gov/waste-toxics/reducing-toxic-chemicals/addressing-priority-toxic-chemicals/pfas",
    "https://dec.ny.gov/pfas",
    "https://www.nj.gov/dep/watersupply/pfas/",
    "https://www.courtlistener.com/api/rest/v4/search/?q=PFAS",
    # EU + global treaty pressure
    "https://echa.europa.eu/registry-of-restriction-intentions/-/registry-of-restriction-intentions/q?p_p_id=com_liferay_portal_search_web_portlet_SearchPortlet_INSTANCE_restriction_intentions",
    "https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas",
    "https://echa.europa.eu/substances-of-very-high-concern-identification/-/substance-designation/-/substance/100.001.017",
    "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R1021",
    "https://eur-lex.europa.eu/eli/dir/2020/2184/oj",
    "http://chm.pops.int/TheConvention/ThePOPs/TheNewPOPs/tabid/2511/Default.aspx",
    "http://chm.pops.int/Implementation/NationalImplementationPlans/NIPTransmission/tabid/253/Default.aspx",
    # Canada federal
    "https://www.canada.ca/en/health-canada/services/chemical-substances/other-chemical-substances-interest/per-polyfluoroalkyl-substances.html",
    "https://www.canada.ca/en/environment-climate-change/services/management-toxic-substances/list-canadian-environmental-protection-act/perfluorooctane-sulfonate.html",
    "https://gazette.gc.ca/index-eng.html",
}

ACTIVE_URLS = {
    # Federal context / inventory
    "https://www.epa.gov/pfas",
    "https://comptox.epa.gov/dashboard/chemical-lists/PFASMASTER",
    # UK + Nordics + Netherlands + Michigan
    "https://www.hse.gov.uk/reach/",
    "https://www.gov.uk/government/publications/environmental-risk-evaluation-reports-per-and-polyfluoroalkyl-substances-pfas",
    "https://www.gov.uk/government/publications/pfas-plan/pfas-plan-building-a-safer-future-together",
    "https://www.michigan.gov/pfasresponse",
    "https://mst.dk/erhverv/sikker-kemi/kemikalier/fokus-paa-saerlige-stoffer/pfas",
    "https://www.miljodirektoratet.no/sok/?q=PFAS",
    "https://www.umweltbundesamt.de/en/search?query=PFAS",
    "https://www.kemi.se/en/chemical-substances-and-materials/highly-fluorinated-substances",
    "https://www.rivm.nl/en/pfas",
    # APAC enacted tracks (important but not first-order Chemours trigger daily)
    "https://www.env.go.jp/water/",
    "https://www.nea.gov.sg/docs/default-source/default-document-library/phase-out-of-fire-fighting-foams-containing-pfas-chemicals-listed-under-the-stockholm-convention_15mar24.pdf",
    "https://www.nea.gov.sg/docs/default-source/hs/industry-guideline-on-the-phase-out-of-pfas-containing-firefighting-foams.pdf",
    "https://www.cha.gov.tw/fp-193-6212-09aa4-2.html",
    # High-value secondary tracker
    "https://www.epa.gov/newsroom/browse-news-releases?search_api_fulltext=pfas",
    "https://pfas-1.itrcweb.org/",
    "https://www.naag.org/attorneys-general/attorney-general-journal/?s=pfas",
    "https://legiscan.com/gaits/search?keyword=PFAS",
    "https://echa.europa.eu/search-for-chemicals?query=tfa",
}


MISSING_PRIORITY_SOURCES = [
    {
        "source": "PACER direct integration (AFFF litigation docket tracking)",
        "url": "https://pacer.uscourts.gov/",
        "priority": "critical",
        "reason": "CourtListener is live as surrogate; direct PACER integration remains a design spike.",
    },
]


def classify_source(entry: URLSource) -> SourceClassification:
    tier_value = getattr(entry.tier, "value", str(entry.tier))
    apac_countries = {"Japan", "South Korea", "Taiwan", "Australia", "India", "China", "Singapore"}
    weekly_countries = {"UK", "United Kingdom", "Denmark", "Norway", "Germany", "Sweden", "Netherlands", "Canada"}

    if entry.url in CRITICAL_URLS:
        priority = SourcePriority.CRITICAL.value
        cadence = "daily"
        rationale = "Direct Chemours regulatory/litigation exposure."
    elif entry.country in apac_countries and tier_value in {"primary", "document"}:
        priority = SourcePriority.CRITICAL.value
        cadence = "daily"
        rationale = "Chemours-requested APAC active monitoring source."
    elif entry.country in apac_countries and tier_value == "secondary":
        priority = SourcePriority.ACTIVE.value
        cadence = "weekly"
        rationale = "APAC supporting tracker; monitored but not core primary source."
    elif entry.country in weekly_countries:
        priority = SourcePriority.ACTIVE.value
        cadence = "weekly"
        rationale = "Tier 2 jurisdiction per Chemours monitoring strategy."
    elif entry.url in ACTIVE_URLS:
        priority = SourcePriority.ACTIVE.value
        cadence = "weekly"
        rationale = "Important signal source; monitor but not daily-critical."
    else:
        priority = SourcePriority.SWEEP.value
        cadence = "monthly"
        rationale = "Long-tail / regional watchlist; monthly sweep is sufficient."

    return SourceClassification(
        url=entry.url,
        label=entry.label,
        country=entry.country,
        tier=tier_value,
        priority=priority,
        cadence=cadence,
        rationale=rationale,
    )


def classify_all(entries: Iterable[URLSource]) -> List[SourceClassification]:
    return [classify_source(entry) for entry in entries]


def select_sources(entries: Iterable[URLSource], profile: str = RunProfile.PRIORITY.value) -> List[URLSource]:
    profile_value = (profile or RunProfile.PRIORITY.value).lower()
    selected: List[URLSource] = []
    for entry in entries:
        cls = classify_source(entry)
        if profile_value == RunProfile.FULL.value:
            selected.append(entry)
        elif profile_value == RunProfile.CRITICAL.value:
            if cls.priority == SourcePriority.CRITICAL.value:
                selected.append(entry)
        elif profile_value == RunProfile.ACTIVE.value:
            if cls.priority == SourcePriority.ACTIVE.value:
                selected.append(entry)
        elif profile_value == RunProfile.SWEEP.value:
            if cls.priority == SourcePriority.SWEEP.value:
                selected.append(entry)
        else:  # default priority profile
            if cls.priority in {SourcePriority.CRITICAL.value, SourcePriority.ACTIVE.value}:
                selected.append(entry)
    return selected


def classification_summary(entries: Iterable[URLSource]) -> Dict[str, int]:
    counts = {
        SourcePriority.CRITICAL.value: 0,
        SourcePriority.ACTIVE.value: 0,
        SourcePriority.SWEEP.value: 0,
    }
    for entry in entries:
        cls = classify_source(entry)
        counts[cls.priority] += 1
    counts["total"] = sum(counts.values())
    return counts
