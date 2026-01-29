"""Core answer models for BoundState."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AnswerSeverity(str, Enum):
    """Severity / strictness of an answer."""

    OK = "ok"
    CAUTION = "caution"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    """Minimal reference to evidence supporting an answer."""

    source_id: str = Field(
        description="Identifier for the evidence source (e.g. document ID).",
    )
    location: Optional[str] = Field(
        default=None,
        description="Location within the source (e.g. section, page).",
    )
    summary: Optional[str] = Field(
        default=None,
        description="Short description of why this evidence is relevant.",
    )


class EngineAnswer(BaseModel):
    """Generic answer produced by the core engine."""

    classification: AnswerSeverity = Field(
        description="Overall severity / compatibility classification.",
    )
    rationale: str = Field(
        description="Short explanation suitable for UI.",
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Evidence items supporting this answer.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional extra notes or caveats.",
    )
