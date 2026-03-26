import { useCallback, useEffect, useState } from "react";

import { ApiError, apiStream } from "@/lib/apiClient";
import { fetchAegisChatPing } from "@/lib/chat/api";
import type { AegisChatStreamEvent, AnswerSurfaceHint, ChatUiMessage } from "@/lib/chat/types";

function createMessageId(prefix: string) {
  return `${prefix}-${globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2, 10)}`;
}

function appendChunk(existing: string, next: string) {
  if (!existing) return next;
  if (!next) return existing;
  if (next.startsWith(".") || next.startsWith(",") || next.startsWith(";") || next.startsWith(":")) {
    return `${existing}${next}`;
  }
  return `${existing} ${next}`;
}

type UseChatArgs = {
  pageId: string;
  pageLabel: string;
  surfaceHint: AnswerSurfaceHint;
};

export function useChat({ pageId, pageLabel, surfaceHint }: UseChatArgs) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [serviceHealthy, setServiceHealthy] = useState(true);
  const [llmAvailable, setLlmAvailable] = useState(true);
  const [runtimeLabel, setRuntimeLabel] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchAegisChatPing()
      .then((runtime) => {
        if (!active) return;
        setServiceHealthy(true);
        setLlmAvailable(runtime.llm_available);
        setRuntimeLabel(runtime.detail ?? null);
      })
      .catch(() => {
        if (!active) return;
        setServiceHealthy(false);
        setLlmAvailable(false);
        setRuntimeLabel("AegisChat runtime status could not be loaded.");
      });

    return () => {
      active = false;
    };
  }, []);

  const sendMessage = useCallback(async (raw: string) => {
    const message = raw.trim();
    if (!message || isSending) return;

    const userId = createMessageId("user");
    const assistantId = createMessageId("assistant");

    setError(null);
    setIsSending(true);
    setServiceHealthy(true);
    setMessages((current) => [
      ...current,
      {
        id: userId,
        role: "user",
        content: message,
        citations: [],
        handoffTargets: [],
        clarificationQuestions: [],
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        handoffTargets: [],
        clarificationQuestions: [],
        isStreaming: true,
      },
    ]);

    try {
      await apiStream("/api/v1/chat/stream", {
        message,
        page_id: pageId,
        answer_surface_hint: {
          ...surfaceHint,
          page_id: pageId,
          page_label: pageLabel,
        },
        session_id: sessionId,
      }, {
        onEvent: (event: AegisChatStreamEvent) => {
          setMessages((current) => current.map((entry) => {
            if (entry.id !== assistantId) return entry;

            if (event.type === "meta") {
              return {
                ...entry,
                status: event.status,
                questionType: event.question_type,
                deterministic: event.deterministic,
              };
            }

            if (event.type === "text") {
              return {
                ...entry,
                content: appendChunk(entry.content, event.text),
              };
            }

            if (event.type === "done") {
              setSessionId(event.session_id);
              if (event.fallback_reason) {
                setLlmAvailable(false);
                setRuntimeLabel(event.fallback_reason);
              } else if (event.provider_used) {
                setLlmAvailable(true);
                setRuntimeLabel(
                  `Frontier reasoning available via ${event.provider_used}${event.model_used ? ` / ${event.model_used}` : ""}.`,
                );
              }
              return {
                ...entry,
                citations: event.citations,
                handoffTargets: event.handoff_targets,
                clarificationQuestions: event.clarification_questions,
                providerUsed: event.provider_used ?? null,
                modelUsed: event.model_used ?? null,
                llmAttempted: event.llm_attempted ?? false,
                fallbackReason: event.fallback_reason ?? null,
                isStreaming: false,
              };
            }

            if (event.type === "error") {
              setError(event.message);
              setServiceHealthy(false);
              return {
                ...entry,
                content: event.message,
                status: "ERROR",
                isStreaming: false,
              };
            }

            if (event.type === "text_end") {
              return { ...entry, isStreaming: false };
            }

            return entry;
          }));
        },
      });
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "Unable to reach AegisChat right now.";
      setError(detail);
      setServiceHealthy(false);
      setMessages((current) => current.map((entry) => (
        entry.id === assistantId
          ? {
              ...entry,
              content: detail,
              status: "ERROR",
              isStreaming: false,
            }
          : entry
      )));
    } finally {
      setIsSending(false);
    }
  }, [isSending, pageId, pageLabel, sessionId, surfaceHint]);

  return {
    open,
    setOpen,
    messages,
    isSending,
      error,
      serviceHealthy,
      llmAvailable,
      runtimeLabel,
      starterQuestions: surfaceHint.starter_questions ?? [],
      sendMessage,
  };
}
