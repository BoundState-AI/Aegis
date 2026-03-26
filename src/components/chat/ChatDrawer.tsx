import { Badge } from "@/components/ui/badge";
import { useTranslation } from "react-i18next";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessageList } from "@/components/chat/ChatMessageList";
import type { ChatUiMessage } from "@/lib/chat/types";

type ChatDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pageLabel: string;
  messages: ChatUiMessage[];
  isSending: boolean;
  error: string | null;
  serviceHealthy: boolean;
  llmAvailable: boolean;
  runtimeLabel: string | null;
  starterQuestions: string[];
  onSend: (message: string) => Promise<void> | void;
};

export function ChatDrawer({
  open,
  onOpenChange,
  pageLabel,
  messages,
  isSending,
  error,
  serviceHealthy,
  llmAvailable,
  runtimeLabel,
  starterQuestions,
  onSend,
}: ChatDrawerProps) {
  const { t } = useTranslation();
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-[460px] p-0 sm:max-w-[460px]">
        <div className="flex h-full flex-col bg-gray-50">
          <SheetHeader className="border-b border-gray-200 px-6 py-5">
            <div className="flex items-center gap-2">
              <SheetTitle>{t("chat.title")}</SheetTitle>
              <Badge variant="outline" className="border-daikin-blue/30 bg-daikin-blue/10 text-daikin-blue">
                {pageLabel}
              </Badge>
            </div>
            <SheetDescription>
              {t("chat.description")}
            </SheetDescription>
            {serviceHealthy && !llmAvailable && (
              <p className="text-xs text-red-600">
                {runtimeLabel || t("chat.runtime.degraded")}
              </p>
            )}
            {!serviceHealthy && (
              <p className="text-xs text-red-600">
                {t("chat.runtime.healthUnavailable")}
              </p>
            )}
            {error && (
              <p className="text-xs text-red-600">{error}</p>
            )}
          </SheetHeader>
          <div className="flex-1 px-6 py-4">
            <ChatMessageList messages={messages} />
          </div>
          <div className="px-6 pb-6">
            <ChatInput
              isSending={isSending}
              onSend={onSend}
              starterQuestions={starterQuestions}
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
