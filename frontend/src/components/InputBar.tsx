import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";

const InputBar = () => {
  const [text, setText] = useState("");
  const isStreaming = useAppStore((s) => s.isStreaming);
  const addMessage = useAppStore((s) => s.addMessage);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    addMessage({
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    });
    setText("");
    // In real app: trigger SSE streaming here
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
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
          className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 font-body"
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
