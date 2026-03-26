#!/usr/bin/env python3
"""
Chat models for AEGIS bounded page chat.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ChatStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    HANDOFF_REQUIRED = "HANDOFF_REQUIRED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    REFUSED = "REFUSED"
    ERROR = "ERROR"


class ClarificationField(BaseModel):
    field: str
    required_for: list[str] = Field(default_factory=list)
    source: str = "visible_state"
    allowed_values: list[str] = Field(default_factory=list)


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_id: str
    label: str
    claim_types: list[str] = Field(default_factory=list)
    payload: Any = None


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sources: list[EvidenceSource] = Field(default_factory=list)


class AnswerSurfaceHint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page_id: Optional[str] = None
    page_label: Optional[str] = None
    module_version: Optional[str] = None
    supported_question_types: list[str] = Field(default_factory=list)
    forbidden_question_types: list[str] = Field(default_factory=list)
    clarification_fields: list[ClarificationField] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    handoff_targets: list[str] = Field(default_factory=list)
    visible_state: dict[str, Any] = Field(default_factory=dict)
    evidence_bundle: EvidenceBundle = Field(default_factory=EvidenceBundle)
    starter_questions: list[str] = Field(default_factory=list)


class AuthoritativeAnswerSurface(BaseModel):
    page_id: str
    page_label: str
    module_version: str = "1.0"
    supported_question_types: list[str] = Field(default_factory=list)
    forbidden_question_types: list[str] = Field(default_factory=list)
    clarification_fields: list[ClarificationField] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    handoff_targets: list[str] = Field(default_factory=list)
    visible_state: dict[str, Any] = Field(default_factory=dict)
    evidence_bundle: EvidenceBundle = Field(default_factory=EvidenceBundle)
    starter_questions: list[str] = Field(default_factory=list)


class SurfaceDiscrepancy(BaseModel):
    field: str
    reason: str
    hint_value: Any = None
    authoritative_value: Any = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    page_id: str = Field(min_length=1)
    answer_surface_hint: AnswerSurfaceHint
    session_id: Optional[str] = None


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatDecision(BaseModel):
    status: ChatStatus
    question_type: str
    response_text: str
    citations: list[str] = Field(default_factory=list)
    handoff_targets: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    deterministic: bool = True


class ChatDonePayload(BaseModel):
    session_id: str = Field(default_factory=lambda: f"chat-{uuid4().hex[:12]}")
    citations: list[str] = Field(default_factory=list)
    handoff_targets: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    discrepancies: list[SurfaceDiscrepancy] = Field(default_factory=list)
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    llm_attempted: bool = False
    fallback_reason: Optional[str] = None


class ChatPingResponse(BaseModel):
    status: str
    llm_enabled: bool
    llm_available: bool
    deterministic_fallback_available: bool = True
    provider: Optional[str] = None
    model: Optional[str] = None
    detail: Optional[str] = None
