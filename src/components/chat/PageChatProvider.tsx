import type { ReactNode } from "react";

import { ChatDrawer } from "@/components/chat/ChatDrawer";
import { ChatFAB } from "@/components/chat/ChatFAB";
import { useChat } from "@/hooks/use-chat";
import type { AnswerSurfaceHint } from "@/lib/chat/types";

type PageChatProviderProps = {
  pageId: string;
  pageLabel: string;
  surfaceHint: AnswerSurfaceHint;
  children: ReactNode;
};

export function PageChatProvider({ pageId, pageLabel, surfaceHint, children }: PageChatProviderProps) {
  const chat = useChat({ pageId, pageLabel, surfaceHint });

  return (
    <>
      {children}
      <ChatFAB onClick={() => chat.setOpen(true)} />
      <ChatDrawer
        open={chat.open}
        onOpenChange={chat.setOpen}
        pageLabel={pageLabel}
        messages={chat.messages}
        isSending={chat.isSending}
        error={chat.error}
        serviceHealthy={chat.serviceHealthy}
        llmAvailable={chat.llmAvailable}
        runtimeLabel={chat.runtimeLabel}
        starterQuestions={chat.starterQuestions}
        onSend={chat.sendMessage}
      />
    </>
  );
}
