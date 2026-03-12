import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { Components } from "react-markdown";
import type { Message, RetrievedChunk } from "@/types";
import { useAppStore } from "@/store/useAppStore";
import { useCallback, useMemo } from "react";

interface AssistantMessageProps {
  message: Message;
}

const CITE_RE = /\[(\d+)\]/g;

const stripUuidPrefix = (name: string) =>
  name.replace(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_/,
    "",
  );

/**
 * Replace [1], [2] etc. with inline HTML <cite> tags.
 * rehype-raw passes these through to React, where we handle them
 * via a custom `cite` component — no tree walking needed.
 */
function insertCiteHtml(markdown: string): string {
  return markdown.replace(CITE_RE, (_match, num) => `<cite data-num="${num}"></cite>`);
}

const CitationBadge = ({
  num,
  chunk,
}: {
  num: number;
  chunk?: RetrievedChunk;
}) => {
  const setHighlightedChunkId = useAppStore((s) => s.setHighlightedChunkId);

  const handleClick = useCallback(() => {
    if (!chunk?.id) return;
    setHighlightedChunkId(chunk.id);
    const el = document.getElementById(`chunk-${chunk.id}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => setHighlightedChunkId(null), 3000);
  }, [chunk, setHighlightedChunkId]);

  const label = chunk
    ? `${stripUuidPrefix(chunk.title || chunk.source)}${chunk.year ? `, ${chunk.year}` : ""}`
    : `Source ${num}`;

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-baseline gap-0.5 mx-0.5 text-[11px] italic text-primary/80 hover:text-primary hover:underline underline-offset-2 transition-colors cursor-pointer align-baseline leading-none"
      title={label}
    >
      <span className="inline-flex items-center justify-center min-w-[1rem] h-[1rem] px-[3px] text-[9px] font-bold not-italic rounded-full bg-primary/15 text-primary leading-none">
        {num}
      </span>
    </button>
  );
};

const AssistantMessage = ({ message }: AssistantMessageProps) => {
  const chunks = message.chunks;

  const processedContent = useMemo(
    () => insertCiteHtml(message.content),
    [message.content]
  );

  const components: Components = useMemo(
    () => ({
      // Handle <cite data-num="N"> tags inserted by insertCiteHtml
      cite: ({ node, ...props }: any) => {
        const num = parseInt(props["data-num"], 10);
        if (isNaN(num)) return <cite {...props} />;
        const chunk =
          chunks && num >= 1 && num <= chunks.length
            ? chunks[num - 1]
            : undefined;
        return <CitationBadge num={num} chunk={chunk} />;
      },
      p: ({ children }) => (
        <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
      ),
      li: ({ children }) => (
        <li className="leading-relaxed">{children}</li>
      ),
      td: ({ children }) => (
        <td className="px-2 py-1">{children}</td>
      ),
      h1: ({ children }) => (
        <h1 className="text-lg font-display font-semibold mt-4 mb-2">
          {children}
        </h1>
      ),
      h2: ({ children }) => (
        <h2 className="text-base font-display font-semibold mt-3 mb-2">
          {children}
        </h2>
      ),
      h3: ({ children }) => (
        <h3 className="text-sm font-display font-semibold mt-3 mb-1">
          {children}
        </h3>
      ),
      ul: ({ children }) => (
        <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>
      ),
      ol: ({ children }) => (
        <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>
      ),
      blockquote: ({ children }) => (
        <blockquote className="border-l-2 border-primary/40 pl-3 my-3 italic text-muted-foreground">
          {children}
        </blockquote>
      ),
      code: ({ className, children }) => {
        const isBlock = className?.includes("language-");
        if (isBlock) {
          return (
            <pre className="bg-muted rounded-md p-3 my-3 overflow-x-auto text-xs">
              <code className={className}>{children}</code>
            </pre>
          );
        }
        return (
          <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">
            {children}
          </code>
        );
      },
      table: ({ children }) => (
        <div className="overflow-x-auto my-3">
          <table className="min-w-full text-xs border border-border rounded">
            {children}
          </table>
        </div>
      ),
      th: ({ children }) => (
        <th className="px-2 py-1 text-left font-semibold bg-muted border-b border-border">
          {children}
        </th>
      ),
      strong: ({ children }) => (
        <strong className="font-semibold text-foreground">{children}</strong>
      ),
    }),
    [chunks]
  );

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        <div className="rounded-xl rounded-tl-sm bg-card border border-border px-4 py-3 shadow-sm">
          <div className="text-sm text-foreground font-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={components}
            >
              {processedContent}
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
