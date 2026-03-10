import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";
import type { Citation } from "@/types";

interface CitationChipProps {
  citation: Citation;
}

const CitationChip = ({ citation }: CitationChipProps) => {
  const setHighlightedChunkId = useAppStore((s) => s.setHighlightedChunkId);
  const activeChunks = useAppStore((s) => s.activeChunks);
  const highlightedChunkId = useAppStore((s) => s.highlightedChunkId);

  const matchingChunk = activeChunks.find(
    (c) => c.source === citation.sourceFile
  );

  const isHighlighted = matchingChunk && highlightedChunkId === matchingChunk.id;

  if (!matchingChunk) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border border-muted text-muted-foreground"
        title="Source chunk not found"
      >
        [{citation.ref}]
      </span>
    );
  }

  return (
    <button
      onClick={() => {
        setHighlightedChunkId(isHighlighted ? null : matchingChunk.id);
      }}
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium transition-all cursor-pointer",
        "border border-primary/30 hover:border-primary",
        isHighlighted
          ? "bg-primary text-primary-foreground"
          : "bg-primary/10 text-foreground hover:bg-primary/20"
      )}
    >
      [{citation.ref}]
    </button>
  );
};

export default CitationChip;
