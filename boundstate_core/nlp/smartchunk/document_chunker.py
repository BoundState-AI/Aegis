#!/usr/bin/env python3
"""
BoundState AI 2025

Athena Document Intelligence System - Smart Chunking Module

Version: 1.0.0
Module: document_chunker.py
System: Amentum Athena Document Intelligence Platform
Classification: For Official Use Only (FOUO)
Last Modified: 2025-01-03

Change Log:
- 1.0.1 (2025-09-10): Default tokenizer updated to intfloat/e5-large-v2

Co-Authored-By: Claude Opus 4.0 <noreply@anthropic.com>
Co-Authored-By: Fran OpenAI o3/4.0/4.5 <noreply@openai.com>
Co-Authored-By: Grok 4.0 <noreply@x.ai>
Co-Authored-By: Dr. Joseph Wilde, BoundState AI

This module provides intelligent document chunking with profile-based adaptation.
Supports multiple document types with NASA-compliant traceability.

NASA/Defense Compliance:
    - SWE-013: Software configuration management
    - SWE-033: Requirements traceability
    - SWE-079: Design documentation
    - NASA-STD-8739.8B: Software assurance

Author: BoundState Team
Created: 2025
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Tuple, Optional

from transformers import AutoTokenizer

# Try to import ChunkProfile, create a minimal one if not available
try:
    from adaptive_chunk_profile import ChunkProfile
except ImportError:
    from dataclasses import dataclass
    from typing import List
    
    @dataclass
    class ChunkProfile:
        chunk_size: int = 384
        overlap: int = 64
        section_detection: bool = True
        rationale: List[str] = None
        
        def __post_init__(self):
            if self.rationale is None:
                self.rationale = ["Default profile"]

__all__ = [
    "DocumentChunker",
    "ChunkingMode",
    "ChunkResult",
    "ChunkingProfiles",
]

logger = logging.getLogger(__name__)

class ChunkingMode(str, Enum):
    """Chunking strategy modes for Athena.

    Compliance: SWE-079
    """
    ADAPTIVE = "adaptive"  # Full smart chunking
    FIXED = "fixed"  # Legacy 420-token mode
    HYBRID = "hybrid"  # Smart for known types, fixed for others
    PROFILE = "profile"  # Use specific named profile

@dataclass
class ChunkResult:
    """Individual chunk with metadata.

    Compliance: SWE-079
    """
    text: str
    token_count: int
    chunk_index: int
    total_chunks: int
    metadata: dict[str, Any]
    source_span: Tuple[int, int]  # Start, end char positions
    profile_used: str
    contains_table: bool = False
    contains_requirements: bool = False
    source: str = ""  # Traceability per NASA-STD-8739.8B

class ChunkingProfiles:
    """Pre-configured profiles for different document types."""
    DENSE_TABULAR = ChunkProfile(
        chunk_size=256,
        overlap=32,
        section_detection=False,
        rationale=["Optimized for spreadsheets and dense tables"],
    )
    TECHNICAL_NARRATIVE = ChunkProfile(
        chunk_size=384,
        overlap=64,
        section_detection=True,
        rationale=["Balanced for technical documentation"],
    )
    REGULATORY_COMPLIANT = ChunkProfile(
        chunk_size=384,
        overlap=96,
        section_detection=True,
        rationale=["NASA-compliant with high overlap for traceability"],
    )
    PRESENTATION_SLIDES = ChunkProfile(
        chunk_size=256,
        overlap=0,
        section_detection=False,
        rationale=["Slide-based atomic chunks"],
    )
    TEST_REPORT = ChunkProfile(
        chunk_size=512,
        overlap=64,
        section_detection=True,
        rationale=["Preserves test data tables"],
    )
    ATHENA_LEGACY = ChunkProfile(
        chunk_size=420,
        overlap=60,
        section_detection=False,
        rationale=["Backwards compatible with existing Athena"],
    )

class DocumentChunker:
    """Main chunking implementation with tokenization.

    Compliance: SWE-033, SWE-079
    """
    __safety_critical__: bool = True

    def __init__(self, tokenizer_model: str = "intfloat/e5-large-v2"):
        """Initialize with tokenizer.

        Args:
            tokenizer_model: Hugging Face tokenizer model name
        """
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_model,
            trust_remote_code=True,
            use_fast=True,
        )
        self.__safety_critical__ = True

    def chunk_document(
        self,
        text: str,
        profile: ChunkProfile,
        file_metadata: dict[str, Any] | None = None,
        source: str = "",
    ) -> List[ChunkResult]:
        """Chunk document text according to profile.

        Args:
            text: Document text content
            profile: Chunking profile to use
            file_metadata: Optional file-level metadata
            source: Source identifier for traceability

        Returns:
            List of chunk results with metadata

        Compliance: SWE-033
        """
        chunks = []
        enc_full = self.tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
        )
        tokens = enc_full["input_ids"]
        offsets = enc_full["offset_mapping"]
        total_tokens = len(tokens)
        chunk_size = max(profile.chunk_size, 64)  # Enforce minimum
        overlap = max(profile.overlap, 0)
        if overlap >= chunk_size:
            overlap = max(chunk_size // 5, 0)  # prevent non-forward progress

        # Section detection if enabled
        if profile.section_detection:
            sections = self._detect_sections(text)
        else:
            sections = [(0, len(text))]

        chunk_index = 0
        for section_start, section_end in sections:
            section_text = text[section_start:section_end]
            enc_sec = self.tokenizer(
                section_text,
                add_special_tokens=False,
                return_offsets_mapping=True,
            )
            section_tokens = enc_sec["input_ids"]
            section_offsets = enc_sec["offset_mapping"]

            if not section_tokens:
                continue

            pos = 0
            while pos < len(section_tokens):
                chunk_end = min(pos + chunk_size, len(section_tokens))
                # Compute accurate char bounds using token offsets
                start_char = section_offsets[pos][0] if pos < len(section_offsets) else 0
                end_char = section_offsets[chunk_end - 1][1] if chunk_end - 1 < len(section_offsets) else len(section_text)
                # Slice by chars for decode stability
                chunk_text = section_text[start_char:end_char]

                # Detect special content
                contains_table = self._detect_table(chunk_text)
                contains_reqs = self._detect_requirements(chunk_text)

                # Create chunk result
                chunk = ChunkResult(
                    text=chunk_text,
                    token_count=(chunk_end - pos),
                    chunk_index=chunk_index,
                    total_chunks=-1,
                    metadata={
                        "section_index": sections.index((section_start, section_end)),
                        "file_metadata": file_metadata or {},
                    },
                    source_span=(
                        section_start + start_char,
                        section_start + end_char,
                    ),
                    profile_used=profile.rationale[0] if profile.rationale else "default",
                    contains_table=contains_table,
                    contains_requirements=contains_reqs,
                    source=source,
                )
                chunks.append(chunk)
                chunk_index += 1
                step = max(chunk_size - overlap, 1)
                pos += step
                if pos + overlap >= len(section_tokens):
                    break

        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        logger.info(
            f"Created {len(chunks)} chunks from {source} using profile "
            f"{profile.rationale[0] if profile.rationale else 'default'}",
            extra={"req_id": str(chunk_index)},
        )
        return chunks

    def _detect_sections(self, text: str) -> List[Tuple[int, int]]:
        """Detect section boundaries in text."""
        sections = []
        pattern = re.compile(r"^\d+\.\s+[A-Z]", re.MULTILINE)
        matches = list(pattern.finditer(text))

        if not matches:
            return [(0, len(text))]

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((start, end))
        return sections

    def _detect_table(self, text: str) -> bool:
        """Detect if chunk contains a table."""
        # Stricter signals to avoid false-positives on hyphens
        has_pipes = text.count("|") >= 3
        ascii_box = ("┌" in text and "┐" in text) or ("│" in text and "─" in text)
        md_header = "Table " in text or "table " in text
        return has_pipes or ascii_box or md_header

    def _detect_requirements(self, text: str) -> bool:
        """Detect if chunk contains requirements."""
        req_words = ["shall", "must", "required", "REQ-", "SWE-"]
        text_lower = text.lower()
        return any(word.lower() in text_lower for word in req_words)
