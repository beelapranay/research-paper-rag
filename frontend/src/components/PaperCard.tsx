import { Trash2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import type { Paper } from "@/types";

interface PaperCardProps {
  paper: Paper;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
}

const statusDot: Record<Paper["status"], string> = {
  indexed: "bg-score-high",
  indexing: "bg-score-mid animate-pulse-soft",
  processing: "bg-score-mid animate-pulse-soft",
  failed: "bg-score-low",
};

const PaperCard = ({ paper, selected, onToggle, onDelete }: PaperCardProps) => {
  return (
    <div className="group flex items-start gap-2.5 rounded-md px-3 py-2 w-full box-border overflow-hidden hover:bg-accent/60 transition-colors">
      <Checkbox
        checked={selected}
        onCheckedChange={onToggle}
        disabled={paper.status !== "indexed"}
        className="mt-1 border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={cn("h-2 w-2 rounded-full shrink-0", statusDot[paper.status])} />
          <p className="text-sm font-medium truncate leading-tight">{paper.title}</p>
        </div>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};

export default PaperCard;
