import { BookOpen } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import UploadZone from "./UploadZone";
import PaperCard from "./PaperCard";
import { ScrollArea } from "@/components/ui/scroll-area";

const LeftSidebar = () => {
  const papers = useAppStore((s) => s.papers);
  const selectedPaperIds = useAppStore((s) => s.selectedPaperIds);
  const togglePaperSelection = useAppStore((s) => s.togglePaperSelection);
  const removePaper = useAppStore((s) => s.removePaper);
  const selectAllPapers = useAppStore((s) => s.selectAllPapers);
  const deselectAllPapers = useAppStore((s) => s.deselectAllPapers);

  const indexedCount = papers.filter((p) => p.status === "indexed").length;
  const allSelected = indexedCount > 0 && selectedPaperIds.size === indexedCount;

  const handleUpload = (files: File[]) => {
    // Mock: add papers with indexing status
    files.forEach((file) => {
      const id = crypto.randomUUID();
      useAppStore.getState().addPaper({
        id,
        title: file.name.replace(".pdf", ""),
        authors: "Unknown",
        year: new Date().getFullYear(),
        status: "indexing",
        filename: file.name,
      });
      // Simulate indexing completing
      setTimeout(() => {
        useAppStore.getState().updatePaperStatus(id, "indexed");
      }, 3000);
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="font-display text-lg font-semibold">Paper Library</h2>
        </div>
        <UploadZone onUpload={handleUpload} />
      </div>

      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <span className="text-xs text-muted-foreground font-medium">
          {papers.length} paper{papers.length !== 1 ? "s" : ""}
        </span>
        <button
          onClick={allSelected ? deselectAllPapers : selectAllPapers}
          className="text-xs text-primary hover:underline font-medium"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-0.5">
          {papers.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              selected={selectedPaperIds.has(paper.id)}
              onToggle={() => togglePaperSelection(paper.id)}
              onDelete={() => removePaper(paper.id)}
            />
          ))}
          {papers.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">
              Upload PDFs to get started
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

export default LeftSidebar;
