import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message } from "@/types";
import { useAppStore } from "@/store/useAppStore";
import { useCallback, useMemo } from "react";

interface AssistantMessageProps {
  message: Message;
}

const CITE_RE = /\[(\d+)\]/g;

const CitationBadge = ({ num, chunkId }: { num: number; chunkId?: string }) => {
  const setHighlightedChunkId = useAppStore((s) => s.setHighlightedChunkId);

  const handleClick = useCallback(() => {
    if (!chunkId) return;
    setHighlightedChunkId(chunkId);
    const el = document.getElementById(`chunk-${chunkId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => setHighlightedChunkId(null), 3000);
  }, [chunkId, setHighlightedChunkId]);

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 mx-0.5 text-[10px] font-bold rounded-full bg-primary/15 text-primary hover:bg-primary/25 transition-colors cursor-pointer align-super leading-none"
      title={chunkId ? `Source ${num} — click to view` : `Source ${num}`}
    >
      {num}
    </button>
  );
};

function injectCitations(
  text: string,
  chunks: Message["chunks"]
): (string | JSX.Element)[] {
  const result: (string | JSX.Element)[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(CITE_RE)) {
    const start = match.index!;
    if (start > lastIndex) {
      result.push(text.slice(lastIndex, start));
    }
    const num = parseInt(match[1], 10);
    const chunk = chunks && num >= 1 && num <= chunks.length ? chunks[num - 1] : undefined;
    result.push(
      <CitationBadge key={`cite-${start}`} num={num} chunkId={chunk?.id} />
    );
    lastIndex = start + match[0].length;
  }
  if (lastIndex < text.length) {
    result.push(text.slice(lastIndex));
  }
  return result;
}

const AssistantMessage = ({ message }: AssistantMessageProps) => {
  const chunks = message.chunks;

  const components: Components = useMemo(
    () => ({
      p: ({ children }) => {
        const processed = processChildren(children, chunks);
        return <p>{processed}</p>;
      },
      li: ({ children }) => {
        const processed = processChildren(children, chunks);
        return <li>{processed}</li>;
      },
      td: ({ children }) => {
        const processed = processChildren(children, chunks);
        return <td>{processed}</td>;
      },
    }),
    [chunks]
  );

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        <div className="rounded-xl rounded-tl-sm bg-card border border-border px-4 py-3 shadow-sm">
          <div className="prose prose-sm max-w-none text-foreground prose-headings:font-display prose-headings:text-foreground prose-strong:text-foreground prose-p:leading-relaxed">
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

function processChildren(
  children: React.ReactNode,
  chunks: Message["chunks"]
): React.ReactNode {
  if (!children) return children;

  const childArray = Array.isArray(children) ? children : [children];
  return childArray.flatMap((child, i) => {
    if (typeof child === "string" && CITE_RE.test(child)) {
      return injectCitations(child, chunks);
    }
    return child;
  });
}

export default AssistantMessage;
