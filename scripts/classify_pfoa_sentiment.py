#!/usr/bin/env python3
"""
PFOA (Perfluorooctanoic Acid) Publication Sentiment Classifier.

Pipeline:
  1. Pull all PFOA paper PMIDs from PubMed E-utilities (1980-2025)
  2. Fetch titles + abstracts via efetch XML
  3. Classify each paper's sentiment using Claude Sonnet
  4. Aggregate by year and output sentiment breakdowns

Usage:
  # Full pipeline
  uv run python scripts/classify_pfoa_sentiment.py

  # Just pull PubMed data (no Sonnet)
  uv run python scripts/classify_pfoa_sentiment.py --pull-only

  # Just classify (assumes raw data already pulled)
  uv run python scripts/classify_pfoa_sentiment.py --classify-only

  # Aggregate existing classifications into backtest
  uv run python scripts/classify_pfoa_sentiment.py --aggregate-only

BoundState AI 2025
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any
import urllib.request
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "boundstate_aegis" / "data" / "evidence"
RAW_PATH = EVIDENCE_DIR / "pfoa_papers_raw.json"
CLASSIFIED_PATH = EVIDENCE_DIR / "pfoa_sentiment_classified.json"
BACKTEST_PATH = EVIDENCE_DIR / "pfoa_backtest.json"

# ---------------------------------------------------------------------------
# PubMed E-utilities
# ---------------------------------------------------------------------------

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_QUERY = '"perfluorooctanoic acid" OR "PFOA" OR "335-67-1" OR "APFO" OR "ammonium perfluorooctanoate"'
YEARS = range(1980, 2026)
RATE_LIMIT_SEC = 0.34  # ~3 requests/sec (NCBI policy without API key)


def pubmed_esearch(query: str, year: int) -> list[str]:
    """Search PubMed for PMIDs matching query in a given year."""
    url = (
        f"{PUBMED_BASE}/esearch.fcgi?db=pubmed"
        f"&term={urllib.request.quote(query)}"
        f"&mindate={year}/01/01&maxdate={year}/12/31"
        f"&datetype=pdat&retmax=2000&retmode=json"
    )
    time.sleep(RATE_LIMIT_SEC)
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids


def pubmed_efetch(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch title + abstract for a list of PMIDs."""
    if not pmids:
        return []

    papers = []
    # Process in batches of 50
    for i in range(0, len(pmids), 50):
        batch = pmids[i : i + 50]
        ids_str = ",".join(batch)
        url = (
            f"{PUBMED_BASE}/efetch.fcgi?db=pubmed"
            f"&id={ids_str}&rettype=abstract&retmode=xml"
        )
        time.sleep(RATE_LIMIT_SEC)
        with urllib.request.urlopen(url) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            abstract_el = article.find(".//Abstract")

            pmid = pmid_el.text if pmid_el is not None else ""
            title = title_el.text if title_el is not None else ""

            # Assemble abstract from all AbstractText elements
            abstract_parts = []
            if abstract_el is not None:
                for part in abstract_el.findall("AbstractText"):
                    label = part.get("Label", "")
                    text = "".join(part.itertext()).strip()
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            abstract = " ".join(abstract_parts)

            # Extract year from PubDate
            year_el = article.find(".//PubDate/Year")
            medline_el = article.find(".//MedlineDate")
            if year_el is not None:
                pub_year = int(year_el.text)
            elif medline_el is not None and medline_el.text:
                pub_year = int(medline_el.text[:4])
            else:
                pub_year = 0

            # Journal
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else ""

            papers.append({
                "pmid": pmid,
                "title": title or "",
                "abstract": abstract,
                "year": pub_year,
                "journal": journal,
            })

        logger.info(f"  Fetched batch {i // 50 + 1}: {len(batch)} PMIDs")

    return papers


def pull_pubmed_data() -> list[dict[str, Any]]:
    """Pull all PFOA papers from PubMed by year."""
    all_papers = []
    all_pmids = set()

    for year in YEARS:
        pmids = pubmed_esearch(SEARCH_QUERY, year)
        new_pmids = [p for p in pmids if p not in all_pmids]
        all_pmids.update(new_pmids)
        logger.info(f"{year}: {len(pmids)} results, {len(new_pmids)} new PMIDs")

        if new_pmids:
            papers = pubmed_efetch(new_pmids)
            # Override year with search year for consistency
            for p in papers:
                if p["year"] == 0:
                    p["year"] = year
            all_papers.extend(papers)

    logger.info(f"Total papers pulled: {len(all_papers)}")

    # Save raw data
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved raw data to {RAW_PATH}")

    return all_papers


# ---------------------------------------------------------------------------
# Sonnet Classification
# ---------------------------------------------------------------------------

CLASSIFICATION_PROMPT = """You are classifying peer-reviewed papers about PFAS compounds (specifically PFOA / Perfluorooctanoic Acid) by their research sentiment and intent.

For each paper below, classify it into exactly ONE of these categories:

1. CELEBRATION (+1.0): Synthesis of new materials, novel properties discovered, application development, performance characterization — papers that say "look what we can make/do with this compound"
2. UTILITY (+0.5): Analytical method development, processing techniques, measurement tools, detection method validation — papers about "here's how to work with or detect this"
3. DETECTION (0.0): Environmental occurrence studies, monitoring campaigns, finding the compound in water/soil/air/biota, concentration measurements — papers saying "we found this compound somewhere"
4. QUESTIONING (-0.5): Persistence studies, bioaccumulation, environmental fate & transport, degradation kinetics, partitioning — papers asking "where does this go? does it break down?"
5. ALARM (-1.0): Health effects, toxicology, exposure assessment, adverse outcomes, risk assessment, epidemiology — papers saying "this compound is harming organisms/people"
6. RECKONING (-1.0): Regulatory analysis, water treatment/remediation, policy discussion, litigation context, removal technologies — papers about "government/lawyers are involved" or "how do we clean this up"

Important guidance:
- A paper about developing a METHOD to detect PFOA in water = UTILITY (focus is the method)
- A paper REPORTING PFOA concentrations found in a river = DETECTION (focus is the occurrence)
- A paper studying whether PFOA persists in groundwater = QUESTIONING (focus is fate)
- A paper on PFOA causing cancer in mice = ALARM (focus is harm)
- A paper on activated carbon removing PFOA from drinking water = RECKONING (focus is remediation)
- Review papers: classify by the dominant theme of the review
- Early papers (1980s-1990s) about fluoropolymer processing = CELEBRATION or UTILITY

Return a JSON array. Each element: {"pmid": "...", "category": "...", "score": ..., "confidence": 0.0-1.0, "reasoning": "one sentence"}

Papers to classify:
"""


def classify_papers(papers: list[dict[str, Any]], resume_from: int = 0) -> list[dict[str, Any]]:
    """Classify papers using Claude Sonnet in batches."""
    import anthropic

    client = anthropic.Anthropic()
    batch_size = 15

    # Load existing classifications if resuming
    classified = []
    if resume_from > 0 and CLASSIFIED_PATH.exists():
        with open(CLASSIFIED_PATH, encoding="utf-8") as f:
            classified = json.load(f)
        logger.info(f"Loaded {len(classified)} existing classifications, resuming from {resume_from}")

    # Skip already classified papers
    papers_to_classify = papers[resume_from:]

    for i in range(0, len(papers_to_classify), batch_size):
        batch = papers_to_classify[i : i + batch_size]
        batch_num = (resume_from + i) // batch_size + 1
        total_batches = (len(papers) + batch_size - 1) // batch_size

        # Build paper descriptions
        paper_text = ""
        for p in batch:
            abstract_snippet = p["abstract"][:500] if p["abstract"] else "(no abstract available)"
            paper_text += (
                f"\nPMID: {p['pmid']}\n"
                f"Year: {p['year']}\n"
                f"Title: {p['title']}\n"
                f"Abstract: {abstract_snippet}\n"
                f"---\n"
            )

        prompt = CLASSIFICATION_PROMPT + paper_text

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse JSON from response
            text = response.content[0].text.strip()
            # Handle markdown code blocks
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            batch_results = json.loads(text)

            # Merge with paper metadata
            pmid_to_result = {str(r["pmid"]): r for r in batch_results}
            for p in batch:
                result = pmid_to_result.get(p["pmid"], {})
                classified.append({
                    "pmid": p["pmid"],
                    "year": p["year"],
                    "title": p["title"],
                    "journal": p["journal"],
                    "category": result.get("category", "DETECTION"),
                    "score": result.get("score", 0.0),
                    "confidence": result.get("confidence", 0.5),
                    "reasoning": result.get("reasoning", "classification unavailable"),
                })

            logger.info(
                f"  Batch {batch_num}/{total_batches}: "
                f"classified {len(batch_results)} papers"
            )

        except Exception as e:
            logger.error(f"  Batch {batch_num} failed: {e}")
            # Fallback: mark as DETECTION with low confidence
            for p in batch:
                classified.append({
                    "pmid": p["pmid"],
                    "year": p["year"],
                    "title": p["title"],
                    "journal": p["journal"],
                    "category": "DETECTION",
                    "score": 0.0,
                    "confidence": 0.0,
                    "reasoning": f"classification failed: {e}",
                })

        # Save checkpoint every 10 batches
        if (i // batch_size + 1) % 10 == 0:
            with open(CLASSIFIED_PATH, "w", encoding="utf-8") as f:
                json.dump(classified, f, indent=2, ensure_ascii=False)
            logger.info(f"  Checkpoint saved: {len(classified)} classifications")

        # Small delay between batches
        time.sleep(0.5)

    # Save classified data
    with open(CLASSIFIED_PATH, "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(classified)} classifications to {CLASSIFIED_PATH}")

    return classified


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

CATEGORY_SCORES = {
    "CELEBRATION": 1.0,
    "UTILITY": 0.5,
    "DETECTION": 0.0,
    "QUESTIONING": -0.5,
    "ALARM": -1.0,
    "RECKONING": -1.0,
}


def aggregate_sentiment(classified: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Aggregate per-paper classifications into year-by-year sentiment breakdowns."""
    yearly: dict[int, dict[str, int]] = {}

    for paper in classified:
        year = paper["year"]
        cat = paper["category"].upper()
        if year not in yearly:
            yearly[year] = {
                "celebration": 0,
                "utility": 0,
                "detection": 0,
                "questioning": 0,
                "alarm": 0,
                "reckoning": 0,
            }
        key = cat.lower()
        if key in yearly[year]:
            yearly[year][key] += 1

    # Compute cumulative sentiment
    cumulative = 0.0
    result = {}
    for year in sorted(yearly.keys()):
        counts = yearly[year]
        year_score = sum(
            counts[cat.lower()] * score
            for cat, score in CATEGORY_SCORES.items()
        )
        cumulative += year_score
        result[year] = {
            "sentiment": counts,
            "year_sentiment_score": round(year_score, 1),
            "cumulative_sentiment": round(cumulative, 1),
        }

    return result


def update_backtest(yearly_sentiment: dict[int, dict[str, Any]]) -> None:
    """Update pfoa_backtest.json with sentiment breakdowns."""
    with open(BACKTEST_PATH, encoding="utf-8") as f:
        backtest = json.load(f)

    # Update timeline entries
    for entry in backtest["timeline"]:
        year = entry["year"]
        cumulative_papers = entry.get("cumulative", 0)
        if year in yearly_sentiment:
            entry["sentiment"] = yearly_sentiment[year]["sentiment"]
            entry["cumulative_sentiment"] = yearly_sentiment[year]["cumulative_sentiment"]
            # Normalized sentiment: average sentiment per paper (-1 to +1 scale)
            if cumulative_papers > 0:
                entry["normalized_sentiment"] = round(
                    yearly_sentiment[year]["cumulative_sentiment"] / cumulative_papers, 3
                )
            else:
                entry["normalized_sentiment"] = 0.0
        else:
            # Pre-publication years: no sentiment data
            entry["sentiment"] = {
                "celebration": 0,
                "utility": 0,
                "detection": 0,
                "questioning": 0,
                "alarm": 0,
                "reckoning": 0,
            }
            entry["cumulative_sentiment"] = 0.0
            entry["normalized_sentiment"] = 0.0

    # Add sentiment category metadata
    backtest["sentiment_categories"] = [
        {"id": "celebration", "label": "Celebration", "score": 1.0, "color": "#22c55e",
         "description": "Synthesis, novel properties, applications"},
        {"id": "utility", "label": "Methods & Utility", "score": 0.5, "color": "#86efac",
         "description": "Analytical methods, processing techniques"},
        {"id": "detection", "label": "Detection", "score": 0.0, "color": "#eab308",
         "description": "Environmental occurrence, monitoring"},
        {"id": "questioning", "label": "Questioning", "score": -0.5, "color": "#f97316",
         "description": "Persistence, fate, bioaccumulation"},
        {"id": "alarm", "label": "Alarm", "score": -1.0, "color": "#ef4444",
         "description": "Health effects, toxicology, exposure"},
        {"id": "reckoning", "label": "Reckoning", "score": -1.0, "color": "#991b1b",
         "description": "Regulation, remediation, litigation"},
    ]

    with open(BACKTEST_PATH, "w", encoding="utf-8") as f:
        json.dump(backtest, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated {BACKTEST_PATH} with sentiment data")


def print_review_report(classified: list[dict[str, Any]]) -> None:
    """Print a review report for manual inspection."""
    from collections import Counter

    print("\n" + "=" * 70)
    print("PFOA SENTIMENT CLASSIFICATION REVIEW REPORT")
    print("=" * 70)

    # Overall distribution
    cats = Counter(p["category"] for p in classified)
    total = len(classified)
    print(f"\nTotal papers: {total}")
    print("\nOverall distribution:")
    for cat in ["CELEBRATION", "UTILITY", "DETECTION", "QUESTIONING", "ALARM", "RECKONING"]:
        count = cats.get(cat, 0)
        pct = count / total * 100 if total else 0
        bar = "#" * int(pct / 2)
        print(f"  {cat:14s} {count:4d} ({pct:5.1f}%) {bar}")

    # Per-year breakdown
    print("\nPer-year breakdown:")
    years = sorted(set(p["year"] for p in classified))
    for year in years:
        year_papers = [p for p in classified if p["year"] == year]
        year_cats = Counter(p["category"] for p in year_papers)
        parts = [f"{c}={year_cats.get(c, 0)}" for c in
                 ["CELEBRATION", "UTILITY", "DETECTION", "QUESTIONING", "ALARM", "RECKONING"]
                 if year_cats.get(c, 0) > 0]
        print(f"  {year}: {len(year_papers):3d} papers — {', '.join(parts)}")

    # Low confidence papers (for manual review)
    low_conf = sorted(
        [p for p in classified if p["confidence"] < 0.7],
        key=lambda x: x["confidence"],
    )
    if low_conf:
        print(f"\nLow confidence papers ({len(low_conf)} for review):")
        for p in low_conf[:20]:
            print(f"  [{p['confidence']:.2f}] {p['category']:12s} PMID:{p['pmid']} "
                  f"({p['year']}) {p['title'][:80]}")
            print(f"           Reasoning: {p['reasoning']}")
    else:
        print("\nNo low-confidence papers found.")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PFOA sentiment classifier")
    parser.add_argument("--pull-only", action="store_true", help="Only pull PubMed data")
    parser.add_argument("--classify-only", action="store_true", help="Only classify (raw data must exist)")
    parser.add_argument("--aggregate-only", action="store_true", help="Only aggregate (classifications must exist)")
    parser.add_argument("--resume", type=int, default=0, help="Resume classification from paper index N")
    args = parser.parse_args()

    if args.aggregate_only:
        logger.info("Aggregating existing classifications...")
        with open(CLASSIFIED_PATH, encoding="utf-8") as f:
            classified = json.load(f)
        yearly = aggregate_sentiment(classified)
        update_backtest(yearly)
        print_review_report(classified)
        return

    if args.classify_only:
        logger.info("Loading existing raw data...")
        with open(RAW_PATH, encoding="utf-8") as f:
            papers = json.load(f)
    else:
        logger.info("Step 1: Pulling PFOA papers from PubMed...")
        papers = pull_pubmed_data()
        if args.pull_only:
            logger.info(f"Pull complete. {len(papers)} papers saved to {RAW_PATH}")
            return

    logger.info(f"Step 2: Classifying {len(papers)} papers with Sonnet...")
    classified = classify_papers(papers, resume_from=args.resume)

    logger.info("Step 3: Aggregating by year...")
    yearly = aggregate_sentiment(classified)
    update_backtest(yearly)

    logger.info("Step 4: Review report...")
    print_review_report(classified)

    logger.info("Done.")


if __name__ == "__main__":
    main()
