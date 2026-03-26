export type ChatStatus =
  | "SUPPORTED"
  | "PARTIAL"
  | "CLARIFICATION_REQUIRED"
  | "HANDOFF_REQUIRED"
  | "OUT_OF_SCOPE"
  | "REFUSED"
  | "ERROR";

export interface ClarificationFieldHint {
  field: string;
  required_for?: string[];
  source?: "visible_state" | "user_input";
  allowed_values?: string[];
}

export interface EvidenceSourceHint {
  source_id: string;
  label: string;
  claim_types?: string[];
  payload: unknown;
}

export interface AnswerSurfaceHint {
  page_id?: string;
  page_label?: string;
  locale?: string;
  module_version?: string;
  supported_question_types?: string[];
  forbidden_question_types?: string[];
  clarification_fields?: ClarificationFieldHint[];
  allowed_actions?: string[];
  handoff_targets?: string[];
  visible_state: Record<string, unknown>;
  evidence_bundle?: {
    sources?: EvidenceSourceHint[];
  };
  starter_questions?: string[];
}

export interface ChatUiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: ChatStatus | null;
  questionType?: string | null;
  citations: string[];
  handoffTargets: string[];
  clarificationQuestions: string[];
  deterministic?: boolean;
  isStreaming?: boolean;
  providerUsed?: string | null;
  modelUsed?: string | null;
  llmAttempted?: boolean;
  fallbackReason?: string | null;
}

export interface ChatMetaEvent {
  type: "meta";
  status: ChatStatus;
  page_id: string;
  question_type: string;
  deterministic: boolean;
}

export interface ChatTextEvent {
  type: "text";
  text: string;
}

export interface ChatDoneEvent {
  type: "done";
  session_id: string;
  citations: string[];
  handoff_targets: string[];
  clarification_questions: string[];
  provider_used?: string | null;
  model_used?: string | null;
  llm_attempted?: boolean;
  fallback_reason?: string | null;
  discrepancies: Array<{
    field: string;
    reason: string;
    hint_value?: unknown;
    authoritative_value?: unknown;
  }>;
}

export interface ChatSimpleEvent {
  type: "text_start" | "text_end";
}

export interface ChatErrorEvent {
  type: "error";
  message: string;
}

export interface ChatRuntimeState {
  status: string;
  llm_enabled: boolean;
  llm_available: boolean;
  deterministic_fallback_available: boolean;
  provider?: string | null;
  model?: string | null;
  detail?: string | null;
}

export type AegisChatStreamEvent =
  | ChatMetaEvent
  | ChatTextEvent
  | ChatDoneEvent
  | ChatSimpleEvent
  | ChatErrorEvent;
