import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types";

interface AssistantMessageProps {
  message: Message;
}

const AssistantMessage = ({ message }: AssistantMessageProps) => {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        <div className="rounded-xl rounded-tl-sm bg-card border border-border px-4 py-3 shadow-sm">
          <div className="prose prose-sm max-w-none text-foreground prose-headings:font-display prose-headings:text-foreground prose-strong:text-foreground prose-p:leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
          {message.isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary/60 animate-pulse-soft ml-0.5" />
          )}
        </div>
      </div>
    </div>
  );
};

export default AssistantMessage;
