import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatUiMessage } from "@/lib/chat/types";

type ChatMessageListProps = {
  messages: ChatUiMessage[];
};

export function ChatMessageList({ messages }: ChatMessageListProps) {
  return (
    <ScrollArea className="h-[calc(100vh-260px)] pr-4">
      <div className="space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            <div
              className={
                message.role === "user"
                  ? "max-w-[85%] rounded-2xl bg-daikin-blue px-4 py-3 text-sm text-white"
                  : "max-w-[92%] rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 shadow-sm"
              }
            >
              <p className="whitespace-pre-wrap leading-6">
                {message.content || (message.isStreaming ? "Thinking..." : "")}
              </p>
              {message.clarificationQuestions.length > 0 && (
                <div className="mt-3 space-y-1">
                  {message.clarificationQuestions.map((question) => (
                    <p key={question} className="text-xs text-gray-500">
                      {question}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
