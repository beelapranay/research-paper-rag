import { useAppStore } from "@/store/useAppStore";
import ChunkCard from "./ChunkCard";
import ScoreBreakdownTable from "./ScoreBreakdownTable";
import ReferencedPapersList from "./ReferencedPapersList";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, Layers, BarChart3, BookMarked } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const Section = ({
  title,
  icon: Icon,
  defaultOpen = true,
  children,
}: {
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-2 w-full py-2 px-1 text-sm font-semibold text-foreground hover:text-primary transition-colors">
        <Icon className="h-4 w-4 text-primary" />
        <span className="flex-1 text-left">{title}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="pb-3">{children}</CollapsibleContent>
    </Collapsible>
  );
};

const RightSidebar = () => {
  const activeChunks = useAppStore((s) => s.activeChunks);

  if (activeChunks.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <p className="text-sm text-muted-foreground text-center">
          Retrieval info will appear here after a response
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-1">
        <h2 className="font-display text-lg font-semibold mb-3">Retrieval Info</h2>

        <Section title="Retrieved Chunks" icon={Layers}>
          <div className="space-y-2">
            {activeChunks.map((chunk, i) => (
              <ChunkCard key={chunk.id} chunk={chunk} index={i} />
            ))}
          </div>
        </Section>

        <Section title="Score Breakdown" icon={BarChart3} defaultOpen={false}>
          <ScoreBreakdownTable chunks={activeChunks} />
        </Section>

        <Section title="Papers Referenced" icon={BookMarked}>
          <ReferencedPapersList chunks={activeChunks} />
        </Section>
      </div>
    </ScrollArea>
  );
};

export default RightSidebar;
