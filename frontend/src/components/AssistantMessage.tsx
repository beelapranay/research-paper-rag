import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message, RetrievedChunk } from "@/types";
import { useAppStore } from "@/store/useAppStore";
import { useCallback, useMemo } from "react";

interface AssistantMessageProps {
  message: Message;
}

const CITE_RE = /\[(\d+)\]/g;

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
    ? `${chunk.title || chunk.source}${chunk.year ? `, ${chunk.year}` : ""}`
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
      {chunk && (
        <span className="max-w-[10rem] truncate hidden sm:inline">
          {chunk.title || chunk.source}
        </span>
      )}
    </button>
  );
};

function injectCitations(
  text: string,
  chunks?: RetrievedChunk[]
): (string | JSX.Element)[] {
  const result: (string | JSX.Element)[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(CITE_RE)) {
    const start = match.index!;
    if (start > lastIndex) {
      result.push(text.slice(lastIndex, start));
    }
    const num = parseInt(match[1], 10);
    const chunk =
      chunks && num >= 1 && num <= chunks.length
        ? chunks[num - 1]
        : undefined;
    result.push(
      <CitationBadge key={`cite-${start}-${num}`} num={num} chunk={chunk} />
    );
    lastIndex = start + match[0].length;
  }
  if (lastIndex < text.length) {
    result.push(text.slice(lastIndex));
  }
  return result;
}

function processChildren(
  children: React.ReactNode,
  chunks?: RetrievedChunk[]
): React.ReactNode {
  if (!children) return children;
  const childArray = Array.isArray(children) ? children : [children];
  return childArray.flatMap((child) => {
    if (typeof child === "string" && CITE_RE.test(child)) {
      return injectCitations(child, chunks);
    }
    return child;
  });
}

const AssistantMessage = ({ message }: AssistantMessageProps) => {
  const chunks = message.chunks;

  const components: Components = useMemo(
    () => ({
      p: ({ children }) => (
        <p className="mb-3 last:mb-0 leading-relaxed">
          {processChildren(children, chunks)}
        </p>
      ),
      li: ({ children }) => (
        <li className="leading-relaxed">
          {processChildren(children, chunks)}
        </li>
      ),
      td: ({ children }) => (
        <td className="px-2 py-1">{processChildren(children, chunks)}</td>
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
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
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
