#!/usr/bin/env python3
"""
Real LLM runtime for bounded AEGIS chat with deterministic fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from boundstate_aegis.engines.chat.prompt_builder import build_llm_prompts
from boundstate_aegis.models.chat_models import (
    AuthoritativeAnswerSurface,
    ChatDecision,
    ChatPingResponse,
    ChatTurn,
)

LOGGER = logging.getLogger(__name__)

_ANTHROPIC_MODEL_DEFAULT = "claude-sonnet-4-5-20250929"
_BEDROCK_MODEL_DEFAULT = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
_BEDROCK_MODEL_DEFAULT_GOV = "us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0"
_OPENAI_COMPAT_MODEL_DEFAULT = "gpt-4.1"
_MAX_TOKENS = 900
_TEMPERATURE = 0.1
_TIMEOUT_S = 45


@dataclass(frozen=True)
class ChatLLMResult:
    text: str | None
    provider: str | None
    model: str | None
    attempted: bool
    fallback_reason: str | None = None


def _is_truthy(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_chat_provider_name() -> str:
    configured = os.environ.get("AEGIS_CHAT_LLM_PROVIDER", "").strip()
    if configured:
        return configured.lower()
    fallback = os.environ.get("LLM_PROVIDER", "").strip()
    if fallback:
        return fallback.lower()
    if os.environ.get("AEGIS_ANTHROPIC_API_KEY", "").strip() or os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "anthropic"
    return "bedrock-converse"


def resolve_chat_bedrock_region() -> str:
    for key in ("AEGIS_CHAT_BEDROCK_REGION", "BEDROCK_REGION", "AWS_REGION", "AWS_DEFAULT_REGION"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return "us-east-1"


def resolve_chat_model(provider: str | None = None) -> str:
    explicit = os.environ.get("AEGIS_CHAT_LLM_MODEL", "").strip()
    if explicit:
        return explicit

    provider_name = (provider or resolve_chat_provider_name()).lower()
    if provider_name == "anthropic":
        return os.environ.get("LLM_SONNET_MODEL", "").strip() or _ANTHROPIC_MODEL_DEFAULT
    if provider_name == "openai-compat":
        return os.environ.get("LLM_SONNET_MODEL", "").strip() or _OPENAI_COMPAT_MODEL_DEFAULT

    region = resolve_chat_bedrock_region().lower()
    env_model = os.environ.get("LLM_SONNET_MODEL", "").strip()
    if env_model:
        return env_model
    if region.startswith("us-gov-"):
        return _BEDROCK_MODEL_DEFAULT_GOV
    return _BEDROCK_MODEL_DEFAULT


def chat_llm_enabled() -> bool:
    return _is_truthy(os.environ.get("AEGIS_CHAT_ENABLE_LLM"), True)


def chat_runtime_status() -> ChatPingResponse:
    provider = resolve_chat_provider_name()
    model = resolve_chat_model(provider)

    if not chat_llm_enabled():
        return ChatPingResponse(
            status="degraded",
            llm_enabled=False,
            llm_available=False,
            deterministic_fallback_available=True,
            provider=provider,
            model=model,
            detail="AEGIS_CHAT_ENABLE_LLM is disabled; deterministic bounded chat remains available.",
        )

    if provider == "anthropic":
        api_key = os.environ.get("AEGIS_ANTHROPIC_API_KEY", "").strip() or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return ChatPingResponse(
                status="degraded",
                llm_enabled=True,
                llm_available=False,
                deterministic_fallback_available=True,
                provider=provider,
                model=model,
                detail="Anthropic API key is not configured for AegisChat.",
            )
        return ChatPingResponse(
            status="ok",
            llm_enabled=True,
            llm_available=True,
            deterministic_fallback_available=True,
            provider=provider,
            model=model,
            detail="Frontier reasoning is available through Anthropic.",
        )

    if provider == "openai-compat":
        base_url = os.environ.get("LLM_BASE_URL", "").strip()
        if not base_url:
            return ChatPingResponse(
                status="degraded",
                llm_enabled=True,
                llm_available=False,
                deterministic_fallback_available=True,
                provider=provider,
                model=model,
                detail="LLM_BASE_URL is required for openai-compat chat.",
            )
        return ChatPingResponse(
            status="ok",
            llm_enabled=True,
            llm_available=True,
            deterministic_fallback_available=True,
            provider=provider,
            model=model,
            detail="Frontier reasoning is available through the configured OpenAI-compatible endpoint.",
        )

    if provider == "bedrock-converse":
        try:
            import boto3
            session = boto3.Session(region_name=resolve_chat_bedrock_region())
            credentials = session.get_credentials()
            if credentials is None:
                return ChatPingResponse(
                    status="degraded",
                    llm_enabled=True,
                    llm_available=False,
                    deterministic_fallback_available=True,
                    provider=provider,
                    model=model,
                    detail="AWS credentials are not available for Bedrock chat.",
                )
        except Exception as exc:
            return ChatPingResponse(
                status="degraded",
                llm_enabled=True,
                llm_available=False,
                deterministic_fallback_available=True,
                provider=provider,
                model=model,
                detail=f"Bedrock runtime is not ready: {exc}",
            )
        return ChatPingResponse(
            status="ok",
            llm_enabled=True,
            llm_available=True,
            deterministic_fallback_available=True,
            provider=provider,
            model=model,
            detail=f"Frontier reasoning is available through Bedrock in {resolve_chat_bedrock_region()}.",
        )

    return ChatPingResponse(
        status="degraded",
        llm_enabled=True,
        llm_available=False,
        deterministic_fallback_available=True,
        provider=provider,
        model=model,
        detail=f"Unknown AegisChat provider '{provider}'.",
    )


def _http_json_request(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_anthropic_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in payload.get("content", []):
        if block.get("type") == "text" and str(block.get("text", "")).strip():
            parts.append(str(block.get("text", "")).strip())
    return "\n".join(parts).strip()


def _extract_bedrock_text(payload: dict[str, Any]) -> str:
    output = payload.get("output", {})
    message = output.get("message", {})
    parts: list[str] = []
    for block in message.get("content", []):
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def _extract_openai_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content", "")).strip()


def _call_anthropic(system_prompt: str, user_prompt: str, model: str) -> str:
    api_key = os.environ.get("AEGIS_ANTHROPIC_API_KEY", "").strip() or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Anthropic API key is not configured")

    payload = {
        "model": model,
        "max_tokens": _MAX_TOKENS,
        "temperature": _TEMPERATURE,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    response = _http_json_request(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2024-10-22",
            "content-type": "application/json",
        },
        payload=payload,
    )
    return _extract_anthropic_text(response)


def _call_bedrock(system_prompt: str, user_prompt: str, model: str) -> str:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=resolve_chat_bedrock_region())
    response = client.converse(
        modelId=model,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={
            "maxTokens": _MAX_TOKENS,
            "temperature": _TEMPERATURE,
        },
    )
    return _extract_bedrock_text(response)


def _call_openai_compat(system_prompt: str, user_prompt: str, model: str) -> str:
    base_url = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("LLM_BASE_URL is not configured")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or "no-key"
    response = _http_json_request(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": _MAX_TOKENS,
            "temperature": _TEMPERATURE,
        },
    )
    return _extract_openai_text(response)


def _run_completion(*, provider: str, model: str, system_prompt: str, user_prompt: str) -> str:
    if provider == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, model)
    if provider == "openai-compat":
        return _call_openai_compat(system_prompt, user_prompt, model)
    if provider == "bedrock-converse":
        return _call_bedrock(system_prompt, user_prompt, model)
    raise ValueError(f"Unsupported chat provider '{provider}'")


async def maybe_generate_llm_response(
    *,
    surface: AuthoritativeAnswerSurface,
    question_type: str,
    user_message: str,
    history: list[ChatTurn],
    evidence: dict[str, Any],
    deterministic_decision: ChatDecision,
) -> ChatLLMResult:
    runtime = chat_runtime_status()
    if not runtime.llm_enabled:
        return ChatLLMResult(
            text=None,
            provider=runtime.provider,
            model=runtime.model,
            attempted=False,
            fallback_reason=runtime.detail,
        )
    if not runtime.llm_available:
        return ChatLLMResult(
            text=None,
            provider=runtime.provider,
            model=runtime.model,
            attempted=False,
            fallback_reason=runtime.detail,
        )

    system_prompt, user_prompt = build_llm_prompts(
        surface=surface,
        question_type=question_type,
        user_message=user_message,
        history=history,
        evidence=evidence,
        deterministic_decision=deterministic_decision,
    )

    provider = runtime.provider or resolve_chat_provider_name()
    model = runtime.model or resolve_chat_model(provider)
    t0 = time.monotonic()
    try:
        text = await asyncio.to_thread(
            _run_completion,
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as exc:
        LOGGER.warning("AegisChat LLM call failed; using deterministic fallback: %s", exc)
        return ChatLLMResult(
            text=None,
            provider=provider,
            model=model,
            attempted=True,
            fallback_reason=f"Frontier reasoning unavailable: {exc}",
        )
    except Exception as exc:  # pragma: no cover - runtime guard
        LOGGER.exception("Unexpected AegisChat LLM failure")
        return ChatLLMResult(
            text=None,
            provider=provider,
            model=model,
            attempted=True,
            fallback_reason=f"Frontier reasoning unavailable: {exc}",
        )

    latency_ms = (time.monotonic() - t0) * 1000
    cleaned = (text or "").strip()
    if not cleaned:
        return ChatLLMResult(
            text=None,
            provider=provider,
            model=model,
            attempted=True,
            fallback_reason="Frontier reasoning returned no text; deterministic fallback used.",
        )

    LOGGER.info(
        "AegisChat LLM response generated via %s model=%s latency_ms=%.1f",
        provider,
        model,
        latency_ms,
    )
    return ChatLLMResult(
        text=cleaned,
        provider=provider,
        model=model,
        attempted=True,
        fallback_reason=None,
    )
