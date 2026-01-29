#!/usr/bin/env python3
"""
BoundState AI 2025

Athena Document Intelligence System - Adapter Module

Version: 2.0.0
Module: athena_adapter.py
System: Amentum Athena Document Intelligence Platform
Classification: For Official Use Only (FOUO)
Last Modified: 2025-01-03

Change Log:
- 2.0.0 (2025-01-03): Enhanced adapter with improved metadata handling and BM25 hints
- 1.0.0 (2025-01-03): Initial adapter for Athena chunks to section format

Co-Authored-By: Claude Opus 4.0 <noreply@anthropic.com>
Co-Authored-By: Fran OpenAI o3/4.0/4.5 <noreply@openai.com>
Co-Authored-By: Grok 4.0 <noreply@x.ai>
Co-Authored-By: Dr. Joseph Wilde, BoundState AI

This module provides the adapter layer to convert Athena chunks into indexer-ready sections.
Ensures traceability and compliance with NASA standards.

NASA/Defense Compliance:
    - SWE-013: Software configuration management
    - SWE-033: Requirements traceability
    - NASA-STD-8739.8B: Software assurance

Author: BoundState Team
Created: 2025
"""

from __future__ import annotations
from typing import Any, Dict, List
import hashlib
from boundstate_core.config.utils import normalize_doc_id

def chunks_to_sections(chunks: List[dict], base_metadata: dict = None) -> List[Dict[str, Any]]:
    """Convert Athena chunk dicts into indexable 'section' dicts."""
    sections: List[Dict[str, Any]] = []
    base_metadata = base_metadata or {}
    
    for ch in chunks:
        text = ch.get("text", "")
        meta = ch.get("metadata", {})
        src = meta.get("source") or ""
        
        # Use filename from base_metadata if provided, otherwise fall back to metadata
        filename = base_metadata.get("filename") or meta.get("file_metadata", {}).get("filename") or src.split("/")[-1]
        # Normalize base id and construct stable doc_id with version
        base_id = normalize_doc_id(filename)
        version = str(base_metadata.get("version", "1.0"))
        doc_id = f"{base_id}_v{version}"
        
        # Merge base_metadata with chunk metadata
        combined_meta = {**base_metadata, **meta}

        sections.append(
            {
                "text": text,
                "embed_text": text,  # Clean text for semantic embeddings
                "bm25_text": f"{filename}\n{text}".strip(),  # Enriched with title for BM25 keyword matching
                "metadata": combined_meta,
                "doc_id": doc_id,
                "base_doc_id": base_id,
                "file_name": filename,
                "section": str(meta.get("chunk_index", 0)),
                "title": base_metadata.get("title", filename),
                "source": src,
                "tags": meta.get("tags", []),
            }
        )
    return sections

# Backward compatibility alias
athena_chunks_to_sections = chunks_to_sections
