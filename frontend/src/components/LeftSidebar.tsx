import { useEffect, useRef, useState } from "react";
import { BookOpen } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import type { PaperStatus } from "@/types";
import UploadZone from "./UploadZone";
import PaperCard from "./PaperCard";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface PaperResponse {
  id: string;
  source_file: string;
  status: PaperStatus;
  title?: string;
  authors?: string;
  year?: number;
}

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
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  const indexedCount = papers.filter((p) => p.status === "indexed").length;
  const allSelected = indexedCount > 0 && selectedPaperIds.size === indexedCount;

  const handleUpload = async (files: File[]) => {
    if (!files.length) return;

    setIsUploading(true);
    const form = new FormData();
    files.forEach((f) => form.append("files", f));

    try {
      const res = await apiFetch("/papers/upload", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast({
          title: res.status === 409 ? "Duplicate paper" : "Upload failed",
          description: err.detail || "Try again.",
        });
        return;
      }

      const created: PaperResponse[] = await res.json();
      if (!Array.isArray(created)) {
        toast({ title: "Upload failed", description: "Unexpected server response." });
        return;
      }
      created.forEach((p) => {
        addPaper({
          id: p.id,
          title: p.source_file.replace(/\.pdf$/i, ""),
          authors: "Unknown",
          year: new Date().getFullYear(),
          status: p.status,
          filename: p.source_file,
        });
      });

      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
      const poll = async () => {
        try {
          const res2 = await apiFetch("/papers");
          if (!res2.ok) return;
          const data: PaperResponse[] = await res2.json();
          if (!Array.isArray(data)) return;
          data.forEach((p) => {
            updatePaperStatus(p.id, p.status);
            // Update metadata that was resolved during ingestion
            const existing = useAppStore.getState().papers.find((ep) => ep.id === p.id);
            if (existing && p.title && existing.title !== p.title) {
              useAppStore.setState((s) => ({
                papers: s.papers.map((ep) =>
                  ep.id === p.id
                    ? { ...ep, title: p.title || ep.title, authors: p.authors || ep.authors, year: p.year || ep.year }
                    : ep
                ),
              }));
            }
          });
          const hasProcessing = data.some((p) => p.status === "processing" || p.status === "indexing");
          if (hasProcessing) {
            pollTimeoutRef.current = setTimeout(poll, 2000);
          }
        } catch {
          // Network error — stop polling silently
        }
      };
      pollTimeoutRef.current = setTimeout(poll, 2000);
    } finally {
      setIsUploading(false);
    }
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
        {isUploading && (
          <p className="text-xs text-muted-foreground mb-2">Uploading...</p>
        )}
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
        <div className="px-3 py-2 space-y-1">
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
