#!/usr/bin/env python3
"""
ab_chunking_benchmark.py

A/B compare "old path" parsing vs. Athena e5-large-v2 smart chunking.

- Produces token-length histograms
- Prints summary stats
- Writes CSVs with per-chunk metadata for both paths

Usage:
  python ab_chunking_benchmark.py --file /path/to/doc.pdf
  python ab_chunking_benchmark.py --file /path/to/doc.pdf --tokenizer intfloat/e5-large-v2 --mode HYBRID

Notes:
- Place this in your repo root (same folder as parsers.py, athena_integration.py, document_chunker.py).
- If imports fail, edit sys.path to point to your project src directory.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # One chart, default colors only; no style set
from transformers import AutoTokenizer

# Try local imports; adjust as needed
try:
    # Add parent directories to path for boundstate imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Go up to repo root
    sys.path.insert(0, str(Path(__file__).parent))  # Add smartchunk dir
    from boundstate_core.ingestion.parsers import get_parser
    from athena_integration import AthenaIntegration, AthenaChunkingConfig
    from document_chunker import ChunkingMode
    from athena_adapter import chunks_to_sections
except Exception as e:
    print("Import error:", e)
    raise

# Wrapper to match expected interface
def parse_file(file_path):
    """Parse file using boundstate parsers."""
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    parser = get_parser(str(file_path), file_bytes=file_bytes)
    return parser.parse()


def load_tokenizer(name: str) -> AutoTokenizer:
    return AutoTokenizer.from_pretrained(name, trust_remote_code=True, use_fast=True)


def tokenize_len(text: str, tok: AutoTokenizer) -> int:
    return len(tok.encode(text, add_special_tokens=False))


def stats_block(values, label: str) -> str:
    if not values:
        return f"{label}: (no data)"
    return (
        f"{label} n={len(values)} | "
        f"min={min(values)} | "
        f"p25={statistics.quantiles(values, n=4)[0]:.1f} | "
        f"median={statistics.median(values):.1f} | "
        f"p75={statistics.quantiles(values, n=4)[-1]:.1f} | "
        f"max={max(values)} | "
        f"mean={statistics.fmean(values):.1f}"
    )


def run_ab(file_path: Path, tokenizer_name: str, mode: str) -> None:
    tok = load_tokenizer(tokenizer_name)

    # ---- Old path: parser output as-is ----
    base_sections = parse_file(str(file_path)) or []
    base_chunks_text = [s.get("text", "") for s in base_sections if s.get("text")]
    base_token_lengths = [tokenize_len(t, tok) for t in base_chunks_text]

    # ---- Athena path: consolidate then smart-chunk ----
    consolidated = "\n\n".join(base_chunks_text) if base_chunks_text else ""
    athena = AthenaIntegration(
        config=AthenaChunkingConfig(
            mode=ChunkingMode[mode.upper()] if mode else ChunkingMode.HYBRID,
            tokenizer_model=tokenizer_name,
            max_chunk_size=768,
            min_chunk_size=128,
        )
    )
    athena_chunks = athena.process_file(file_path, content=consolidated)
    athena_sections = chunks_to_sections(athena_chunks)
    athena_texts = [s.get("text", "") for s in athena_sections if s.get("text")]
    athena_token_lengths = [tokenize_len(t, tok) for t in athena_texts]

    # ---- Print stats ----
    print(f"\nFile: {file_path}")
    print(stats_block(base_token_lengths, "OLD  (parser-only)"))
    print(stats_block(athena_token_lengths, "NEW  (Athena e5-large-v2)"))

    # ---- Save CSVs ----
    out_dir = Path("ab_chunking_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    base_csv = out_dir / f"{file_path.stem}_old_parser.csv"
    with base_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "token_len", "char_len"])
        for i, t in enumerate(base_chunks_text):
            w.writerow([i, tokenize_len(t, tok), len(t)])

    new_csv = out_dir / f"{file_path.stem}_new_athena.csv"
    with new_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "token_len", "char_len"])
        for i, t in enumerate(athena_texts):
            w.writerow([i, tokenize_len(t, tok), len(t)])

    print(f"CSV written: {base_csv}")
    print(f"CSV written: {new_csv}")

    # ---- Plot histogram (one chart) ----
    plt.figure(figsize=(8, 5))
    plt.hist(base_token_lengths, bins=30, alpha=0.6, label="Old parser-only")
    plt.hist(athena_token_lengths, bins=30, alpha=0.6, label="New Athena smart-chunk")
    plt.title(f"Token count per chunk - {file_path.name}")
    plt.xlabel("Tokens per chunk")
    plt.ylabel("Frequency")
    plt.legend()
    fig_path = out_dir / f"{file_path.stem}_token_hist.png"
    plt.tight_layout()
    plt.savefig(fig_path, dpi=120)
    print(f"Histogram saved: {fig_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", type=str, default=r"C:\Users\wa-jwilde2\athena\test_documents\G9301.1B r00.docx", help="Path to a single document")
    p.add_argument("--tokenizer", type=str, default="intfloat/e5-large-v2")
    p.add_argument("--mode", type=str, default="HYBRID", choices=["HYBRID", "ADAPTIVE", "FIXED", "PROFILE"])
    args = p.parse_args()

    run_ab(Path(args.file).resolve(), args.tokenizer, args.mode)


if __name__ == "__main__":
    main()
