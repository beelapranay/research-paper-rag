import { useState } from "react";
import { BookOpen, Info, PanelLeftClose, PanelRightClose } from "lucide-react";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import LeftSidebar from "@/components/LeftSidebar";
import ChatPanel from "@/components/ChatPanel";
import RightSidebar from "@/components/RightSidebar";

const Index = () => {
  const isMobile = useIsMobile();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-background">
        {/* Mobile header */}
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
      {/* Left sidebar - desktop */}
      <aside className="w-[280px] border-r border-border bg-sidebar shrink-0">
        <LeftSidebar />
      </aside>

      {/* Chat panel - center */}
      <main className="flex-1 min-w-0">
        <ChatPanel />
      </main>

      {/* Right sidebar - desktop */}
      <aside className="w-[320px] border-l border-border bg-sidebar shrink-0">
        <RightSidebar />
      </aside>
    </div>
  );
};

export default Index;
