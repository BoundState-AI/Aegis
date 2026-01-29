#!/usr/bin/env python3
"""
BoundState AI 2025

Athena Document Intelligence System - Smoke Test Tool

Version: 1.0.0
Module: smoke_test_athena_chunking.py
System: Amentum Athena Document Intelligence Platform
Classification: For Official Use Only (FOUO)
Last Modified: 2025-01-03

Change Log:
- 1.0.0 (2025-01-03): Initial smoke test for Athena chunking validation

Co-Authored-By: Claude Opus 4.0 <noreply@anthropic.com>
Co-Authored-By: Fran OpenAI o3/4.0/4.5 <noreply@openai.com>
Co-Authored-By: Grok 4.0 <noreply@x.ai>
Co-Authored-By: Dr. Joseph Wilde, BoundState AI

This module provides end-to-end testing for the Athena smart chunking system.
Validates chunking profiles, token counts, and adapter output.

NASA/Defense Compliance:
    - SWE-013: Software configuration management
    - SWE-033: Requirements traceability
    - NASA-STD-8739.8B: Software assurance

Author: BoundState Team
Created: 2025
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from athena_integration import AthenaIntegration, AthenaChunkingConfig, ChunkingMode
from document_chunker import ChunkingProfiles
from athena_adapter import athena_chunks_to_sections


def _summary(chunks):
    """Generate summary statistics for chunks."""
    token_counts = [c["metadata"]["token_count"] for c in chunks]
    has_tables = sum(1 for c in chunks if c["metadata"].get("contains_table"))
    has_reqs = sum(1 for c in chunks if c["metadata"].get("contains_requirements"))
    return {
        "n_chunks": len(chunks),
        "min_tokens": min(token_counts) if token_counts else 0,
        "max_tokens": max(token_counts) if token_counts else 0,
        "avg_tokens": round(statistics.mean(token_counts), 1) if token_counts else 0.0,
        "p50_tokens": statistics.median(token_counts) if token_counts else 0,
        "tables": has_tables,
        "requirements": has_reqs,
    }


def run_smoke(file_path: Path,
              mode: str = "HYBRID",
              tokenizer_model: str = "intfloat/e5-large-v2",
              override_profile: str | None = None):
    """Run smoke test on a document file.
    
    Args:
        file_path: Path to document to test
        mode: Chunking mode (ADAPTIVE, FIXED, HYBRID, PROFILE)
        tokenizer_model: HuggingFace model for tokenization
        override_profile: Optional profile override
    """
    # 1) Configure Athena chunking (tokenizer = NV-Embed-v2 by default)
    cfg = AthenaChunkingConfig(
        mode=ChunkingMode(mode.upper()),
        tokenizer_model=tokenizer_model,
        # keep guardrails sensible for NV-Embed-v2
        min_chunk_size=128,
        max_chunk_size=1024,
    )
    ath = AthenaIntegration(config=cfg)

    # Optional explicit profile override
    profile = None
    if override_profile:
        prof_map = {
            "DENSE_TABULAR": ChunkingProfiles.DENSE_TABULAR,
            "TECHNICAL_NARRATIVE": ChunkingProfiles.TECHNICAL_NARRATIVE,
            "REGULATORY_COMPLIANT": ChunkingProfiles.REGULATORY_COMPLIANT,
            "PRESENTATION_SLIDES": ChunkingProfiles.PRESENTATION_SLIDES,
            "TEST_REPORT": ChunkingProfiles.TEST_REPORT,
            "ATHENA_LEGACY": ChunkingProfiles.ATHENA_LEGACY,
        }
        if override_profile not in prof_map:
            raise SystemExit(f"Unknown profile '{override_profile}'. Valid: {', '.join(prof_map)}")
        profile = prof_map[override_profile]

    # 2) Chunk the document
    chunks = ath.process_file(file_path, override_profile=profile)

    # 3) Print a concise report
    s = _summary(chunks)
    print("\n=== ATHENA CHUNKING SMOKE TEST ===")
    print(f"File: {file_path.name}")
    print(f"Mode: {mode}  |  Tokenizer: {tokenizer_model}  |  Profile: {override_profile or 'auto'}")
    print(f"Chunks: {s['n_chunks']}  |  tokens (min/avg/p50/max): "
          f"{s['min_tokens']}/{s['avg_tokens']}/{s['p50_tokens']}/{s['max_tokens']}")
    print(f"Contains tables: {s['tables']}  |  contains requirements: {s['requirements']}\n")

    # Show first 2 chunks (trimmed)
    for c in chunks[:2]:
        idx = c["metadata"]["chunk_index"]
        tks = c["metadata"]["token_count"]
        prof = c["metadata"]["profile"]
        flags = []
        if c["metadata"].get("contains_table"): flags.append("table")
        if c["metadata"].get("contains_requirements"): flags.append("reqs")
        flag_str = f" [{' & '.join(flags)}]" if flags else ""
        print(f"— chunk #{idx}  ({tks} tokens)  profile={prof}{flag_str}")
        print(c["text"][:280].replace("\n", " ") + ("…" if len(c["text"]) > 280 else ""))
        print()

    # 4) Convert to indexer sections via the adapter
    base_meta = {
        "filename": file_path.name,
        "source_path": str(file_path),
        "version": "1.0",
        "version_tuple": (1, 0, 0, ""),
        "doc_type": "",
        "tags": [],
        "title": file_path.stem,
    }
    sections = athena_chunks_to_sections(chunks, base_meta)

    # Sanity checks that SmartIndexer expects:
    required_fields = ("text", "embed_text", "bm25_text", "doc_id", "file_name", "source")
    missing = [f for f in required_fields if f not in sections[0]]
    if missing:
        print(f"[WARN] First section missing fields: {missing}")

    print(f"\nConverted to {len(sections)} sections for indexing.")
    print("Section keys sample:", sorted(list(sections[0].keys()))[:10])
    print("Looks good ✅  (ready for SmartIndexer.add([...]))\n")

    # Guidance hints based on chunk stats
    if s["avg_tokens"] < 200:
        print("[Hint] Average tokens are on the low side. Consider using TECHNICAL_NARRATIVE (≈384–512).")
    if s["avg_tokens"] > 900:
        print("[Hint] Chunks are quite large. Consider lower profile (e.g., 512 w/ overlap) for sharper retrieval.")


def main():
    """Main entry point for smoke test."""
    ap = argparse.ArgumentParser(description="Athena chunking smoke test (NV-Embed-v2 tokenizer).")
    ap.add_argument("file", type=Path, help="Path to a document (pdf/docx/txt)")
    ap.add_argument("--mode", default="HYBRID", choices=["ADAPTIVE", "FIXED", "HYBRID", "PROFILE"])
    ap.add_argument("--tokenizer", default="intfloat/e5-large-v2",
                    help="HF model for tokenization (default: intfloat/e5-large-v2)")
    ap.add_argument("--profile", default=None,
                    help="Optional profile override: DENSE_TABULAR | TECHNICAL_NARRATIVE | "
                         "REGULATORY_COMPLIANT | PRESENTATION_SLIDES | TEST_REPORT | ATHENA_LEGACY")
    args = ap.parse_args()
    
    if not args.file.exists():
        raise SystemExit(f"File not found: {args.file}")
    
    run_smoke(args.file, args.mode, args.tokenizer, args.profile)


if __name__ == "__main__":
    main()
