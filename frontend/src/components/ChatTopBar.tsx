import { FileText, Eraser } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { Button } from "@/components/ui/button";
import ThemeToggle from "./ThemeToggle";

const ChatTopBar = () => {
  const papers = useAppStore((s) => s.papers);
  const selectedPaperIds = useAppStore((s) => s.selectedPaperIds);
  const clearChat = useAppStore((s) => s.clearChat);

  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <FileText className="h-4 w-4" />
        <span>
          Querying{" "}
          <span className="font-semibold text-foreground">{selectedPaperIds.size}</span>{" "}
          of {papers.length} papers
        </span>
      </div>
      <div className="flex items-center gap-1">
        <ThemeToggle />
        <Button variant="ghost" size="sm" onClick={clearChat} className="text-muted-foreground hover:text-foreground">
          <Eraser className="h-3.5 w-3.5 mr-1.5" />
          Clear chat
        </Button>
      </div>
    </div>
  );
};

export default ChatTopBar;
