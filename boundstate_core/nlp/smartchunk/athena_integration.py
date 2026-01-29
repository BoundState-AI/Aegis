#!/usr/bin/env python3
"""
BoundState AI 2025

Athena Document Intelligence System - Integration Module

Version: 1.0.0
Module: athena_integration.py
System: Amentum Athena Document Intelligence Platform
Classification: For Official Use Only (FOUO)
Last Modified: 2025-01-03

Change Log:
- 1.0.0 (2025-01-03): Initial integration layer with adaptive chunking profiles

Co-Authored-By: Claude Opus 4.0 <noreply@anthropic.com>
Co-Authored-By: Fran OpenAI o3/4.0/4.5 <noreply@openai.com>
Co-Authored-By: Grok 4.0 <noreply@x.ai>
Co-Authored-By: Dr. Joseph Wilde, BoundState AI

This module provides the integration layer between smart chunking and Athena indexing.
Supports hybrid chunking modes with profile caching and deep content analysis.

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
import uuid
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, Field, field_validator

# Try to import dependencies, create minimal ones if not available
try:
    from adaptive_chunk_profile import AdaptiveChunkProfile, ChunkProfile
except ImportError:
    from dataclasses import dataclass
    from typing import List, Dict, Any
    
    @dataclass
    class ChunkProfile:
        chunk_size: int = 384
        overlap: int = 64
        section_detection: bool = True
        rationale: List[str] = None
        
        def __post_init__(self):
            if self.rationale is None:
                self.rationale = ["Default profile"]
    
    class AdaptiveChunkProfile:
        def __init__(self, base_profile: ChunkProfile):
            self.base_profile = base_profile
        
        def adapt(self, analysis: Dict[str, Any]) -> ChunkProfile:
            return self.base_profile

try:
    from content_analyzer import ContentAnalyzer
except ImportError:
    class ContentAnalyzer:
        def analyze_sample(self, sample: bytes, deep_scan: bool = True) -> Dict[str, Any]:
            return {
                "is_test_report": False,
                "standards_detected": False,
            }

from document_chunker import ChunkingMode, ChunkingProfiles, ChunkResult, DocumentChunker

__all__ = ["AthenaIntegration", "AthenaChunkingConfig"]

logger = logging.getLogger(__name__)

class AthenaChunkingConfig(BaseModel):
    """Configuration for Athena chunking integration.

    Compliance: SWE-079
    """
    model_config = {"extra": "forbid", "populate_by_name": True}

    mode: ChunkingMode = Field(default=ChunkingMode.HYBRID)
    enable_deep_analysis: bool = Field(default=True)
    cache_profiles: bool = Field(default=True)
    max_chunk_size: int = Field(default=768, ge=128, le=4096)
    min_chunk_size: int = Field(default=64, ge=32, le=512)
    tokenizer_model: str = Field(default="intfloat/e5-large-v2")
    # Optional NASA SW class; only validated if provided
    software_class: str | None = Field(default=None)

    @field_validator("max_chunk_size", mode="after")
    def validate_chunk_sizes(cls, v: int, info: Any) -> int:
        """Ensure max > min chunk size."""
        if "min_chunk_size" in info.data and v <= info.data["min_chunk_size"]:
            raise ValueError("max_chunk_size must exceed min_chunk_size")
        return v

    @field_validator("software_class", mode="after")
    def validate_software_class(cls, v: Any, info: Any) -> Any:
        """Enforce NASA software classification per Appendix D."""
        if v is None:
            return v
        valid = {"A", "B", "C", "D", "E", "F"}
        if v not in valid:
            raise ValueError(f"software_class must be one of {sorted(valid)}")
        return v

class AthenaIntegration:
    """Integration layer for Athena system.

    Compliance: SWE-013, SWE-033
    """
    __safety_critical__: bool = True

    def __init__(
        self,
        config: AthenaChunkingConfig | None = None,
        mode: ChunkingMode | None = None,
        enable_deep_analysis: bool | None = None,
        cache_profiles: bool | None = None,
    ):
        """Initialize Athena integration.

        Args:
            config: Optional configuration object
            mode: Chunking mode override
            enable_deep_analysis: Deep analysis toggle
            cache_profiles: Profile caching toggle

        Compliance: SWE-013
        """
        self.config = config or AthenaChunkingConfig()
        self.mode = mode or self.config.mode
        self.enable_deep_analysis = (
            enable_deep_analysis
            if enable_deep_analysis is not None
            else self.config.enable_deep_analysis
        )
        self.cache_profiles = (
            cache_profiles
            if cache_profiles is not None
            else self.config.cache_profiles
        )
        self.chunker = DocumentChunker(self.config.tokenizer_model)
        self.analyzer = ContentAnalyzer()
        self.profile_cache: dict[str, ChunkProfile] = {}
        self.__safety_critical__ = True

    def process_file(
        self,
        file_path: Path,
        content: str | None = None,
        override_profile: ChunkProfile | None = None,
    ) -> List[dict[str, Any]]:
        """Process file for Athena indexing.

        Args:
            file_path: Path to document
            content: Optional pre-extracted text content
            override_profile: Force specific profile

        Returns:
            Chunks ready for embedding

        Compliance: SWE-033
        """
        try:
            # Get or extract content
            if content is None:
                content = self._extract_content(file_path)

            # Select chunking profile
            if override_profile:
                profile = override_profile
                logger.info(f"Using override profile for {file_path.name}")
            else:
                profile = self._select_profile(file_path, content)

            # Ensure chunk size is within bounds
            if profile.chunk_size > self.config.max_chunk_size:
                profile.chunk_size = self.config.max_chunk_size
            elif profile.chunk_size < self.config.min_chunk_size:
                profile.chunk_size = self.config.min_chunk_size

            # Chunk the document
            chunk_results = self.chunker.chunk_document(
                content,
                profile,
                file_metadata={
                    "filename": file_path.name,
                    "file_type": file_path.suffix,
                    "chunking_mode": self.mode.value,
                },
                source=str(file_path),
            )

            # Convert to Athena format
            athena_chunks = []
            for chunk in chunk_results:
                athena_chunk = {
                    "text": chunk.text,
                    "metadata": {
                        "source": chunk.source,
                        "chunk_index": chunk.chunk_index,
                        "total_chunks": chunk.total_chunks,
                        "token_count": chunk.token_count,
                        "profile": chunk.profile_used,
                        "contains_table": chunk.contains_table,
                        "contains_requirements": chunk.contains_requirements,
                        **chunk.metadata,
                    },
                    "embedding": None,  # To be populated by embedding service
                }
                athena_chunks.append(athena_chunk)

            logger.info(
                f"Processed {file_path.name} with {len(athena_chunks)} chunks",
                extra={"req_id": str(uuid.uuid4())},
            )
            return athena_chunks

        except Exception as e:
            logger.error(
                f"Failed to process {file_path.name}: {str(e)}",
                extra={"req_id": str(uuid.uuid4())},
            )
            raise

    def _select_profile(self, file_path: Path, content: str) -> ChunkProfile:
        """Select appropriate chunking profile.

        Args:
            file_path: Document path
            content: Document content

        Returns:
            Selected chunking profile
        """
        cache_key = str(file_path)

        # Check cache
        if self.cache_profiles and cache_key in self.profile_cache:
            return self.profile_cache[cache_key]

        # Mode-based selection
        if self.mode == ChunkingMode.FIXED:
            profile = ChunkingProfiles.ATHENA_LEGACY
        elif self.mode == ChunkingMode.ADAPTIVE:
            profile = self._adaptive_profile_selection(file_path, content)
        elif self.mode == ChunkingMode.HYBRID:
            if file_path.suffix.lower() in [".pdf", ".docx", ".xlsx", ".pptx"]:
                profile = self._adaptive_profile_selection(file_path, content)
            else:
                profile = ChunkingProfiles.ATHENA_LEGACY
        else:  # PROFILE mode
            profile = ChunkingProfiles.TECHNICAL_NARRATIVE

        # Cache result
        if self.cache_profiles:
            self.profile_cache[cache_key] = profile

        logger.info(
            f"Selected profile for {file_path.name}: "
            f"{profile.rationale[0] if profile.rationale else 'default'}",
            extra={"req_id": str(uuid.uuid4())},
        )
        return profile

    def _adaptive_profile_selection(self, file_path: Path, content: str) -> ChunkProfile:
        """Smart profile selection based on content analysis.

        Args:
            file_path: Document path
            content: Document content

        Returns:
            Adapted chunking profile
        """
        sample = content[:20480].encode("utf-8")
        analysis = self.analyzer.analyze_sample(sample, deep_scan=self.enable_deep_analysis)

        suffix = file_path.suffix.lower()
        if suffix in [".xlsx", ".xls", ".csv"]:
            base_profile = ChunkingProfiles.DENSE_TABULAR
        elif suffix in [".ppt", ".pptx"]:
            base_profile = ChunkingProfiles.PRESENTATION_SLIDES
        elif analysis.get("is_test_report"):
            base_profile = ChunkingProfiles.TEST_REPORT
        elif analysis.get("standards_detected"):
            base_profile = ChunkingProfiles.REGULATORY_COMPLIANT
        else:
            base_profile = ChunkingProfiles.TECHNICAL_NARRATIVE

        if self.enable_deep_analysis:
            adapter = AdaptiveChunkProfile(base_profile=base_profile)
            profile = adapter.adapt(analysis)
        else:
            profile = base_profile

        logger.info(
            f"Adaptive profile for {file_path.name}: "
            f"{profile.rationale[0] if profile.rationale else 'default'}",
            extra={"req_id": str(uuid.uuid4())},
        )
        return profile

    def _extract_content(self, file_path: Path) -> str:
        """Extract text content from file.

        Args:
            file_path: Path to document

        Returns:
            Extracted text content
        """
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(
                f"Failed to extract content from {file_path.name}: {str(e)}",
                extra={"req_id": str(uuid.uuid4())},
            )
            raise
