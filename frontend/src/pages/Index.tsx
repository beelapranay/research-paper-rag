import { useEffect, useState } from "react";
import { BookOpen, Info } from "lucide-react";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import LeftSidebar from "@/components/LeftSidebar";
import ChatPanel from "@/components/ChatPanel";
import RightSidebar from "@/components/RightSidebar";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const isMobile = useIsMobile();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const setPapers = useAppStore((s) => s.setPapers);
  const setMessages = useAppStore((s) => s.setMessages);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    const loadPapers = async () => {
      try {
        const res = await apiFetch("/papers");
        if (cancelled) return;
        if (res.status === 401) {
          navigate("/login");
          return;
        }
        if (!res.ok) {
          toast({ title: "Failed to load papers" });
          return;
        }
        const data = await res.json();
        if (!cancelled) setPapers(data);
      } catch {
        if (!cancelled) toast({ title: "Failed to load papers" });
      }
    };

    const loadChatHistory = async () => {
      try {
        const res = await apiFetch("/chat/history");
        if (cancelled || !res.ok) return;
        const data = await res.json();
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          const messages = data.map((m: any) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            chunks: m.chunks?.map((c: any, i: number) => ({
              id: c.id || `chunk_${i}`,
              content: c.content,
              source: c.source_file,
              title: c.title,
              authors: c.authors || "",
              year: c.year || 0,
              bm25Rank: c.bm25_rank || 0,
              vectorRank: c.vector_rank || 0,
              rrfScore: c.rrf_score || 0,
              rerankScore: c.rerank_score || 0,
            })),
          }));
          setMessages(messages);
        }
      } catch {
        // Chat history is non-critical — fail silently
      }
    };

    loadPapers();
    loadChatHistory();
    return () => { cancelled = true; };
  }, [setPapers, setMessages, toast, navigate]);

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-background">
        <header className="flex items-center justify-between px-3 py-2 border-b border-border bg-background/90 backdrop-blur-sm">
          <Button variant="ghost" size="icon" onClick={() => setLeftOpen(true)}>
            <BookOpen className="h-5 w-5" />
          </Button>
          <h1 className="font-display text-base font-semibold">PaperRAG</h1>
          <Button variant="ghost" size="icon" onClick={() => setRightOpen(true)}>
            <Info className="h-5 w-5" />
          </Button>
        </header>

        <div className="flex-1 overflow-hidden">
          <ChatPanel />
        </div>

        <Sheet open={leftOpen} onOpenChange={setLeftOpen}>
          <SheetContent side="left" className="w-[300px] p-0">
            <SheetHeader className="sr-only">
              <SheetTitle>Paper Library</SheetTitle>
            </SheetHeader>
            <LeftSidebar />
          </SheetContent>
        </Sheet>

        <Sheet open={rightOpen} onOpenChange={setRightOpen}>
          <SheetContent side="right" className="w-[320px] p-0">
            <SheetHeader className="sr-only">
              <SheetTitle>Retrieval Info</SheetTitle>
            </SheetHeader>
            <RightSidebar />
          </SheetContent>
        </Sheet>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      <aside className="w-[280px] border-r border-border bg-sidebar shrink-0 overflow-hidden">
        <LeftSidebar />
      </aside>

      <main className="flex-1 min-w-0">
        <ChatPanel />
      </main>

      <aside className="w-[320px] border-l border-border bg-sidebar shrink-0 overflow-hidden">
        <RightSidebar />
      </aside>
    </div>
  );
};

export default Index;
