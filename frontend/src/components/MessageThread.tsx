import { useRef, useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";
import { ScrollArea } from "@/components/ui/scroll-area";

const MessageThread = () => {
  const messages = useAppStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3 px-8">
          <h2 className="font-display text-2xl font-semibold text-foreground">
            Ask about your papers
          </h2>
          <p className="text-muted-foreground text-sm max-w-md">
            Upload research papers to the library, select which ones to query, and ask questions grounded in your sources.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {messages.map((msg) =>
          msg.role === "user" ? (
            <UserMessage key={msg.id} content={msg.content} />
          ) : (msg.role as string) === "system" ? (
            <div key={msg.id} className="flex justify-center">
              <span className="text-xs text-muted-foreground bg-muted/60 px-3 py-1 rounded-full italic">
                {msg.content}
              </span>
            </div>
          ) : (
            <AssistantMessage key={msg.id} message={msg} />
          )
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
};

export default MessageThread;
