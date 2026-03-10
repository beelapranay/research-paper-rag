import type { RetrievedChunk } from "@/types";

interface ReferencedPapersListProps {
  chunks: RetrievedChunk[];
}

const basename = (source: string) => {
  if (!source) return "unknown";
  return source.replace("\\", "/").split("/").pop() || source;
};

const ReferencedPapersList = ({ chunks }: ReferencedPapersListProps) => {
  const seen = new Set<string>();
  const papers = chunks.filter((c) => {
    if (seen.has(c.source)) return false;
    seen.add(c.source);
    return true;
  });

  return (
    <div className="space-y-1.5">
      {papers.map((paper) => (
        <div key={paper.source} className="flex items-start gap-2 px-1">
          <span className="h-1.5 w-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-xs font-medium text-foreground leading-tight">{paper.authors}</p>
            <p className="text-xs text-muted-foreground">{basename(paper.source)} · {paper.year}</p>
          </div>
        </div>
      ))}
      {papers.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">No papers referenced yet</p>
      )}
    </div>
  );
};

export default ReferencedPapersList;
