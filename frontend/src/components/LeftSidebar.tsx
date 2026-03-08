import { BookOpen } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import UploadZone from "./UploadZone";
import PaperCard from "./PaperCard";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

const LeftSidebar = () => {
  const papers = useAppStore((s) => s.papers);
  const selectedPaperIds = useAppStore((s) => s.selectedPaperIds);
  const togglePaperSelection = useAppStore((s) => s.togglePaperSelection);
  const removePaper = useAppStore((s) => s.removePaper);
  const selectAllPapers = useAppStore((s) => s.selectAllPapers);
  const deselectAllPapers = useAppStore((s) => s.deselectAllPapers);
  const addPaper = useAppStore((s) => s.addPaper);
  const updatePaperStatus = useAppStore((s) => s.updatePaperStatus);
  const { toast } = useToast();

  const indexedCount = papers.filter((p) => p.status === "indexed").length;
  const allSelected = indexedCount > 0 && selectedPaperIds.size === indexedCount;

  const handleUpload = async (files: File[]) => {
    if (!files.length) return;

    const form = new FormData();
    files.forEach((f) => form.append("files", f));

    const res = await apiFetch("/papers/upload", {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast({ title: "Upload failed", description: err.detail || "Try again." });
      return;
    }

    const created = await res.json();
    created.forEach((p: any) => {
      addPaper({
        id: p.id,
        title: p.source_file.replace(/\.pdf$/i, ""),
        authors: "Unknown",
        year: new Date().getFullYear(),
        status: p.status,
        filename: p.source_file,
      });
    });

    // Poll status
    const poll = async () => {
      const res2 = await apiFetch("/papers");
      if (!res2.ok) return;
      const data = await res2.json();
      data.forEach((p: any) => updatePaperStatus(p.id, p.status));
    };
    setTimeout(poll, 2000);
  };

  const handleDelete = async (id: string) => {
    const res = await apiFetch(`/papers/${id}`, { method: "DELETE" });
    if (!res.ok) {
      toast({ title: "Delete failed" });
      return;
    }
    removePaper(id);
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
              onDelete={() => handleDelete(paper.id)}
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
