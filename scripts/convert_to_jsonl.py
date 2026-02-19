#!/usr/bin/env python3
"""
Convert PFAS sentiment classified papers to Bedrock fine-tuning JSONL format.

Input:  genx_sentiment_classified.json + pfoa_sentiment_classified.json
Output: sentinel_train.jsonl + sentinel_val.jsonl

Usage:
    python convert_to_jsonl.py --data-dir D:/BoundState/boundstate_aegis/boundstate_aegis/data/evidence

BoundState AI 2025
Authored-By: Dr. Joseph Wilde
Oracle: Beth (Claude Sonnet 4.6)
"""

import json
import random
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a PFAS scientific literature classifier for regulatory risk analysis.

Classify scientific publications about PFAS compounds into one of six categories based on their content and implications:

CELEBRATION  (score: +1.0) — Synthesis, novel properties, new applications. Positive framing of PFAS utility.
UTILITY      (score: +0.5) — Analytical methods, processing techniques, measurement tools. Neutral/technical.
DETECTION    (score:  0.0) — Environmental occurrence, monitoring, presence studies. Observational.
QUESTIONING  (score: -0.5) — Persistence, fate, bioaccumulation, early concern signals.
ALARM        (score: -1.0) — Health effects, toxicology, exposure studies, adverse outcomes.
RECKONING    (score: -1.0) — Regulation, remediation, litigation, enforcement actions.

Respond with Category, Score, and a one-sentence Reasoning that explains the classification."""

CATEGORY_SCORES = {
    "CELEBRATION": 1.0,
    "UTILITY": 0.5,
    "DETECTION": 0.0,
    "QUESTIONING": -0.5,
    "ALARM": -1.0,
    "RECKONING": -1.0,
}

TRAIN_SPLIT = 0.894  # ~6,400 train / 762 val from 7,162 total

# Balancing targets — cap overrepresented, oversample underrepresented
BALANCE_TARGETS = {
    "ALARM":       1500,
    "DETECTION":   1429,  # keep as-is
    "RECKONING":    977,  # keep as-is
    "QUESTIONING":  848,  # keep as-is
    "UTILITY":      694,  # keep as-is
    "CELEBRATION":  300,  # oversample from 85
}

# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def paper_to_training_pair(paper: dict) -> dict:
    """Convert a classified paper dict to a Bedrock fine-tuning message pair."""
    user_content = (
        f"Title: {paper['title']}\n"
        f"Journal: {paper['journal']}\n"
        f"Year: {paper['year']}"
    )

    assistant_content = (
        f"Category: {paper['category']}\n"
        f"Score: {paper['score']}\n"
        f"Reasoning: {paper['reasoning']}"
    )

    return {
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }


def load_papers(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        papers = json.load(f)
    # Validate required fields
    required = {"pmid", "year", "title", "journal", "category", "score", "confidence", "reasoning"}
    valid = []
    skipped = 0
    for p in papers:
        if required.issubset(p.keys()) and p["category"] in CATEGORY_SCORES:
            valid.append(p)
        else:
            skipped += 1
    if skipped:
        print(f"  Skipped {skipped} invalid entries in {path.name}")
    return valid


def write_jsonl(records: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(records):,} records → {path}")


def balance_dataset(papers: list[dict], seed: int = 42) -> list[dict]:
    """Cap overrepresented classes, oversample underrepresented classes."""
    random.seed(seed)
    by_category: dict[str, list] = {}
    for p in papers:
        by_category.setdefault(p["category"], []).append(p)

    balanced = []
    for cat, target in BALANCE_TARGETS.items():
        pool = by_category.get(cat, [])
        if not pool:
            print(f"  WARNING: No papers found for category {cat}")
            continue
        if len(pool) >= target:
            # Undersample — take random subset
            balanced.extend(random.sample(pool, target))
        else:
            # Oversample — sample with replacement to hit target
            oversampled = pool * (target // len(pool)) + random.sample(pool, target % len(pool))
            balanced.extend(oversampled)
        print(f"  {cat:<12} {len(pool):>5,} → {target:,}")

    random.shuffle(balanced)
    return balanced


def category_distribution(papers: list[dict]) -> dict:
    dist = {}
    for p in papers:
        dist[p["category"]] = dist.get(p["category"], 0) + 1
    return dict(sorted(dist.items()))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert classified PFAS papers to Bedrock fine-tuning JSONL")
    parser.add_argument(
        "--data-dir",
        default="D:/BoundState/boundstate_aegis/boundstate_aegis/data/evidence",
        help="Directory containing classified JSON files"
    )
    parser.add_argument(
        "--output-dir",
        default="D:/BoundState/boundstate_aegis/boundstate_aegis/data/finetune",
        help="Output directory for JSONL files"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible split")
    parser.add_argument("--balance", action="store_true", help="Balance dataset by capping/oversampling per category")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load both files
    print("Loading classified papers...")
    genx_path = data_dir / "genx_sentiment_classified.json"
    pfoa_path = data_dir / "pfoa_sentiment_classified.json"

    genx_papers = load_papers(genx_path)
    pfoa_papers = load_papers(pfoa_path)
    print(f"  GenX: {len(genx_papers):,} papers")
    print(f"  PFOA: {len(pfoa_papers):,} papers")

    all_papers = genx_papers + pfoa_papers
    print(f"  Total: {len(all_papers):,} papers")

    # Category distribution
    print("\nCategory distribution (raw):")
    for cat, count in category_distribution(all_papers).items():
        pct = count / len(all_papers) * 100
        print(f"  {cat:<12} {count:>5,}  ({pct:.1f}%)")

    # Balance if requested
    if args.balance:
        print("\nBalancing dataset...")
        all_papers = balance_dataset(all_papers, seed=args.seed)
        print(f"  Balanced total: {len(all_papers):,} papers")
        print("\nCategory distribution (balanced):")
        for cat, count in category_distribution(all_papers).items():
            pct = count / len(all_papers) * 100
            print(f"  {cat:<12} {count:>5,}  ({pct:.1f}%)")

    # Shuffle and split
    random.seed(args.seed)
    random.shuffle(all_papers)

    split_idx = int(len(all_papers) * TRAIN_SPLIT)
    train_papers = all_papers[:split_idx]
    val_papers = all_papers[split_idx:]

    print(f"\nSplit: {len(train_papers):,} train / {len(val_papers):,} validation")

    # Convert to training pairs
    train_pairs = [paper_to_training_pair(p) for p in train_papers]
    val_pairs = [paper_to_training_pair(p) for p in val_papers]

    # Write JSONL
    print("\nWriting JSONL files...")
    write_jsonl(train_pairs, output_dir / "sentinel_train.jsonl")
    write_jsonl(val_pairs, output_dir / "sentinel_val.jsonl")

    print(f"\nDone. Files ready for Bedrock fine-tuning upload.")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
