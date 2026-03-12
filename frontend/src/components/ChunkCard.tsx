import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";
import type { RetrievedChunk } from "@/types";
import { useState } from "react";

interface ChunkCardProps {
  chunk: RetrievedChunk;
}

const getScoreColor = (score: number) => {
  if (score > 0.7) return "bg-score-high text-white";
  if (score >= 0.4) return "bg-score-mid text-foreground";
  return "bg-score-low text-white";
};

const basename = (source: string) => {
  if (!source) return "unknown";
  return source.replace("\\", "/").split("/").pop() || source;
};

const ChunkCard = ({ chunk }: ChunkCardProps) => {
  const highlightedChunkId = useAppStore((s) => s.highlightedChunkId);
  const isHighlighted = highlightedChunkId === chunk.id;
  const [expanded, setExpanded] = useState(false);

  const truncatedContent = chunk.content.length > 180 && !expanded
    ? chunk.content.slice(0, 180) + "..."
    : chunk.content;

  return (
    <div
      id={`chunk-${chunk.id}`}
      className={cn(
        "rounded-lg border p-3 transition-all duration-300 overflow-hidden",
        isHighlighted
          ? "border-primary bg-chunk-highlight shadow-md ring-1 ring-primary/30"
          : "border-border bg-card hover:border-border/80"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-foreground truncate">
            {chunk.title || basename(chunk.source)}
          </p>
          <p className="text-xs text-muted-foreground break-all">
            {basename(chunk.source)} · {chunk.year}
          </p>
        </div>
        <span className={cn("text-xs font-bold px-2 py-0.5 rounded-full shrink-0", getScoreColor(chunk.rerankScore))}>
          {chunk.rerankScore.toFixed(2)}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground break-words">
        {truncatedContent}
        {chunk.content.length > 180 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-1 text-primary hover:underline font-medium"
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
      </p>
    </div>
  );
};

export default ChunkCard;
