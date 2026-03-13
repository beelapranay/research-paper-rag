import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";
import { apiFetch } from "@/lib/api";

const persistMessage = (id: string, role: string, content: string, chunks?: any[]) => {
  apiFetch("/chat/save", {
    method: "POST",
    body: JSON.stringify({ id, role, content, chunks: chunks || [] }),
  }).catch(() => {});
};

const InputBar = () => {
  const [text, setText] = useState("");
  const isStreaming = useAppStore((s) => s.isStreaming);
  const addMessage = useAppStore((s) => s.addMessage);
  const updateLastAssistantMessage = useAppStore((s) => s.updateLastAssistantMessage);
  const finalizeAssistantMessage = useAppStore((s) => s.finalizeAssistantMessage);
  const setIsStreaming = useAppStore((s) => s.setIsStreaming);
  const selectedPaperIds = useAppStore((s) => s.selectedPaperIds);
  const messages = useAppStore((s) => s.messages);
  const papers = useAppStore((s) => s.papers);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastSentPaperIds = useRef<Set<string> | null>(null);

  const handleSend = async () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    // If paper selection changed since last message, insert a system notice
    if (lastSentPaperIds.current !== null) {
      const prev = lastSentPaperIds.current;
      const curr = selectedPaperIds;
      const changed = prev.size !== curr.size || [...prev].some((id) => !curr.has(id));
      if (changed) {
        const selectedNames = papers
          .filter((p) => curr.has(p.id))
          .map((p) => p.filename)
          .join(", ");
        addMessage({
          id: crypto.randomUUID(),
          role: "system" as any,
          content: `Paper selection changed. Now querying: ${selectedNames || "none"}`,
        });
      }
    }
    lastSentPaperIds.current = new Set(selectedPaperIds);

    const userMsg = { id: crypto.randomUUID(), role: "user" as const, content: trimmed };
    const assistantId = crypto.randomUUID();
    addMessage(userMsg);
    addMessage({ id: assistantId, role: "assistant", content: "", isStreaming: true });
    persistMessage(userMsg.id, "user", trimmed);
    setIsStreaming(true);
    setText("");

    const history = [...messages, userMsg]
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));

    const res = await apiFetch("/chat", {
      method: "POST",
      body: JSON.stringify({
        query: trimmed,
        paper_ids: Array.from(selectedPaperIds),
        chat_history: history,
      }),
    });

    if (!res.ok || !res.body) {
      updateLastAssistantMessage("Error: failed to get response.");
      setIsStreaming(false);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let assistantText = "";
    let finalChunks: any[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (part.startsWith("event: token")) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
          if (dataLine) {
            try {
              const payload = JSON.parse(dataLine.replace("data: ", ""));
              const token = typeof payload?.token === "string" ? payload.token : "";
              assistantText += token;
              updateLastAssistantMessage(assistantText);
            } catch {
              const token = dataLine.replace("data: ", "");
              assistantText += token;
              updateLastAssistantMessage(assistantText);
            }
          }
        }

        if (part.startsWith("event: metadata")) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
          if (dataLine) {
            const payload = JSON.parse(dataLine.replace("data: ", ""));
            finalChunks = (payload.chunks || []).map((c: any, i: number) => ({
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
            }));
          }
        }
      }
    }

    finalizeAssistantMessage(finalChunks);

    // Persist the assistant response with chunk metadata
    const chunksForDb = finalChunks.map((c: any) => ({
      id: c.id,
      content: c.content,
      source_file: c.source,
      title: c.title,
      authors: c.authors,
      year: c.year,
      bm25_rank: c.bm25Rank,
      vector_rank: c.vectorRank,
      rrf_score: c.rrfScore,
      rerank_score: c.rerankScore,
    }));
    persistMessage(assistantId, "assistant", assistantText, chunksForDb);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  }, [text]);

  return (
    <div className="border-t border-border p-3 bg-background/80 backdrop-blur-sm">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your papers..."
          disabled={isStreaming}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 font-body hide-scrollbar"
        />
        <Button
          onClick={handleSend}
          disabled={!text.trim() || isStreaming}
          size="icon"
          className="shrink-0 rounded-lg bg-primary hover:bg-primary/90"
        >
          {isStreaming ? (
            <span className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
};

export default InputBar;
