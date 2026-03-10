import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";
import { apiFetch } from "@/lib/api";

const InputBar = () => {
  const [text, setText] = useState("");
  const isStreaming = useAppStore((s) => s.isStreaming);
  const addMessage = useAppStore((s) => s.addMessage);
  const updateLastAssistantMessage = useAppStore((s) => s.updateLastAssistantMessage);
  const finalizeAssistantMessage = useAppStore((s) => s.finalizeAssistantMessage);
  const setIsStreaming = useAppStore((s) => s.setIsStreaming);
  const selectedPaperIds = useAppStore((s) => s.selectedPaperIds);
  const messages = useAppStore((s) => s.messages);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = async () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    const userMsg = { id: crypto.randomUUID(), role: "user" as const, content: trimmed };
    addMessage(userMsg);
    addMessage({ id: crypto.randomUUID(), role: "assistant", content: "", isStreaming: true });
    setIsStreaming(true);
    setText("");

    const history = [...messages, userMsg].map((m) => ({ role: m.role, content: m.content }));

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
    let finalCitations: any[] = [];
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
            const token = dataLine.replace("data: ", "");
            assistantText += token;
            updateLastAssistantMessage(assistantText);
          }
        }

        if (part.startsWith("event: metadata")) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
          if (dataLine) {
            const payload = JSON.parse(dataLine.replace("data: ", ""));
            finalCitations = payload.citations || [];
            finalChunks = (payload.chunks || []).map((c: any, i: number) => ({
              id: c.id || `chunk_${i}`,
              content: c.content,
              source: c.source_file,
              authors: c.authors || "Unknown",
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

    finalizeAssistantMessage(finalCitations, finalChunks);
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
