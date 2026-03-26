import { useState } from "react";
import { Send } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type ChatInputProps = {
  isSending: boolean;
  onSend: (message: string) => Promise<void> | void;
  starterQuestions: string[];
};

export function ChatInput({ isSending, onSend, starterQuestions }: ChatInputProps) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState("");

  const submit = async () => {
    const next = draft.trim();
    if (!next || isSending) return;
    setDraft("");
    await onSend(next);
  };

  return (
    <div className="space-y-3 border-t border-gray-200 pt-4">
      {starterQuestions.length > 0 && !draft && (
        <div className="flex flex-wrap gap-2">
          {starterQuestions.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => setDraft(question)}
              className="rounded-full border border-gray-300 bg-gray-50 px-3 py-1 text-left text-xs text-gray-600 transition hover:border-daikin-blue hover:text-daikin-blue"
            >
              {question}
            </button>
          ))}
        </div>
      )}
      <Textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submit();
          }
        }}
        placeholder={t("chat.placeholder")}
        className="min-h-[96px] resize-none"
        disabled={isSending}
      />
      <div className="flex justify-end">
        <Button type="button" onClick={() => void submit()} disabled={isSending || !draft.trim()}>
          <Send className="mr-2 h-4 w-4" />
          {isSending ? t("chat.sending") : t("chat.send")}
        </Button>
      </div>
    </div>
  );
}
