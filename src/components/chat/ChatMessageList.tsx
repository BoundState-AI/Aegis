import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatUiMessage } from "@/lib/chat/types";

function statusClass(status: string | null | undefined) {
  switch (status) {
    case "SUPPORTED":
      return "bg-green-100 text-green-700 border-green-300";
    case "PARTIAL":
      return "bg-yellow-100 text-yellow-700 border-yellow-300";
    case "CLARIFICATION_REQUIRED":
      return "bg-blue-100 text-blue-700 border-blue-300";
    case "HANDOFF_REQUIRED":
      return "bg-purple-100 text-purple-700 border-purple-300";
    case "OUT_OF_SCOPE":
    case "REFUSED":
    case "ERROR":
      return "bg-red-100 text-red-700 border-red-300";
    default:
      return "bg-gray-100 text-gray-700 border-gray-300";
  }
}

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
              {message.role === "assistant" && message.status && (
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className={statusClass(message.status)}>
                    {message.status.replaceAll("_", " ")}
                  </Badge>
                  {message.deterministic ? (
                    <Badge variant="outline" className="border-gray-300 bg-gray-50 text-gray-600">
                      Deterministic
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="border-emerald-300 bg-emerald-50 text-emerald-700">
                      Frontier
                    </Badge>
                  )}
                </div>
              )}
              <p className="whitespace-pre-wrap leading-6">
                {message.content || (message.isStreaming ? "Thinking..." : "")}
              </p>
              {message.citations.length > 0 && (
                <p className="mt-3 text-xs text-gray-500">
                  Sources: {message.citations.join(", ")}
                </p>
              )}
              {message.providerUsed && (
                <p className="mt-2 text-xs text-gray-500">
                  Runtime: {message.providerUsed}{message.modelUsed ? ` / ${message.modelUsed}` : ""}
                </p>
              )}
              {message.fallbackReason && (
                <p className="mt-2 text-xs text-gray-500">
                  Fallback: {message.fallbackReason}
                </p>
              )}
              {message.handoffTargets.length > 0 && (
                <p className="mt-2 text-xs text-gray-500">
                  Handoff: {message.handoffTargets.join(", ")}
                </p>
              )}
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
