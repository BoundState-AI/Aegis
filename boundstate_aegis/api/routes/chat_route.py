#!/usr/bin/env python3
"""
Bounded AEGIS chat route.
"""

from __future__ import annotations

import json
import logging
from typing import Iterable

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from boundstate_aegis.engines.chat.answer_surface import build_authoritative_surface
from boundstate_aegis.engines.chat.bouncer import classify_query
from boundstate_aegis.engines.chat.evidence_selector import select_evidence
from boundstate_aegis.engines.chat.llm_runtime import chat_runtime_status, maybe_generate_llm_response
from boundstate_aegis.engines.chat.response_engine import (
    build_deterministic_response,
    clarification_response,
    handoff_response,
    out_of_scope_response,
    refused_response,
)
from boundstate_aegis.engines.chat.session_store import STORE
from boundstate_aegis.models.chat_models import ChatDonePayload, ChatPingResponse, ChatRequest, ChatStatus

router = APIRouter()
LOGGER = logging.getLogger(__name__)


def _sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _chunk_text(text: str, chunk_size: int = 120) -> Iterable[str]:
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > chunk_size and current:
            yield current
            current = word
        else:
            current = candidate
    if current:
        yield current


@router.post("/stream")
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    if request.answer_surface_hint.page_id and request.answer_surface_hint.page_id != request.page_id:
        raise HTTPException(status_code=422, detail="answer_surface_hint.page_id must match page_id when provided")

    try:
        surface, discrepancies = build_authoritative_surface(request.page_id, request.answer_surface_hint)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        LOGGER.exception("Failed to build authoritative answer surface")
        raise HTTPException(status_code=500, detail="Failed to build answer surface") from exc

    session_id = STORE.touch(request.session_id)
    outcome = classify_query(request.message, surface)

    history = STORE.history(session_id)

    if outcome.status == ChatStatus.REFUSED:
        decision = refused_response()
        llm_result = None
    elif outcome.status == ChatStatus.OUT_OF_SCOPE:
        decision = out_of_scope_response(surface)
        llm_result = None
    elif outcome.status == ChatStatus.HANDOFF_REQUIRED:
        decision = handoff_response(surface, outcome.handoff_target)
        llm_result = None
    elif outcome.status == ChatStatus.CLARIFICATION_REQUIRED:
        decision = clarification_response(surface)
        llm_result = None
    else:
        evidence = select_evidence(request.message, surface, outcome.question_type)
        decision = build_deterministic_response(surface, outcome.question_type, evidence)
        llm_result = await maybe_generate_llm_response(
            surface=surface,
            question_type=outcome.question_type,
            user_message=request.message,
            history=history,
            evidence=evidence,
            deterministic_decision=decision,
        )
        if llm_result.text:
            decision_payload = decision.model_dump()
            decision_payload["response_text"] = llm_result.text
            decision_payload["deterministic"] = False
            decision = type(decision)(**decision_payload)

    STORE.append(session_id, request.message, decision.response_text)
    done_payload = ChatDonePayload(
        session_id=session_id,
        citations=decision.citations,
        handoff_targets=decision.handoff_targets,
        clarification_questions=decision.clarification_questions,
        discrepancies=discrepancies,
        provider_used=llm_result.provider if llm_result else None,
        model_used=llm_result.model if llm_result else None,
        llm_attempted=llm_result.attempted if llm_result else False,
        fallback_reason=llm_result.fallback_reason if llm_result else None,
    )

    async def event_stream():
        yield _sse_event({
            "type": "meta",
            "status": decision.status.value,
            "page_id": surface.page_id,
            "question_type": decision.question_type,
            "deterministic": decision.deterministic,
        })
        yield _sse_event({"type": "text_start"})
        for chunk in _chunk_text(decision.response_text):
            yield _sse_event({"type": "text", "text": chunk})
        yield _sse_event({"type": "text_end"})
        yield _sse_event({"type": "done", **done_payload.model_dump()})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/ping", response_model=ChatPingResponse)
async def ping_chat() -> ChatPingResponse:
    return chat_runtime_status()
