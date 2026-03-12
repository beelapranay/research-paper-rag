import type { RetrievedChunk } from "@/types";

interface ScoreBreakdownTableProps {
  chunks: RetrievedChunk[];
}

const basename = (source: string) => {
  if (!source) return "unknown";
  const name = source.replace("\\", "/").split("/").pop() || source;
  return name.replace(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_/,
    "",
  );
};

const ScoreBreakdownTable = ({ chunks }: ScoreBreakdownTableProps) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-1.5 px-2 font-semibold text-muted-foreground">Source</th>
            <th className="text-right py-1.5 px-2 font-semibold text-muted-foreground">BM25</th>
            <th className="text-right py-1.5 px-2 font-semibold text-muted-foreground">Vector</th>
            <th className="text-right py-1.5 px-2 font-semibold text-muted-foreground">RRF</th>
            <th className="text-right py-1.5 px-2 font-semibold text-muted-foreground">Rerank</th>
          </tr>
        </thead>
        <tbody>
          {chunks.map((chunk) => (
            <tr key={chunk.id} className="border-b border-border/50 last:border-0">
              <td className="py-1.5 px-2 text-foreground truncate max-w-[140px]">{basename(chunk.source)}</td>
              <td className="py-1.5 px-2 text-right text-muted-foreground">#{chunk.bm25Rank}</td>
              <td className="py-1.5 px-2 text-right text-muted-foreground">#{chunk.vectorRank}</td>
              <td className="py-1.5 px-2 text-right text-muted-foreground">{chunk.rrfScore.toFixed(3)}</td>
              <td className="py-1.5 px-2 text-right font-medium text-foreground">{chunk.rerankScore.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ScoreBreakdownTable;
