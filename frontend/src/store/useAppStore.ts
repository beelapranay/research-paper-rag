import { create } from "zustand";
import type { Paper, Message, RetrievedChunk } from "@/types";

interface AppState {
  papers: Paper[];
  selectedPaperIds: Set<string>;
  messages: Message[];
  activeChunks: RetrievedChunk[];
  highlightedChunkId: string | null;
  isStreaming: boolean;

  // Paper actions
  setPapers: (papers: Paper[]) => void;
  addPaper: (paper: Paper) => void;
  removePaper: (id: string) => void;
  updatePaperStatus: (id: string, status: Paper["status"]) => void;
  togglePaperSelection: (id: string) => void;
  selectAllPapers: () => void;
  deselectAllPapers: () => void;

  // Chat actions
  addMessage: (message: Message) => void;
  updateLastAssistantMessage: (content: string) => void;
  finalizeAssistantMessage: (chunks: RetrievedChunk[]) => void;
  clearChat: () => void;
  setIsStreaming: (v: boolean) => void;

  // Retrieval actions
  setActiveChunks: (chunks: RetrievedChunk[]) => void;
  setHighlightedChunkId: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  papers: [],
  selectedPaperIds: new Set(),
  messages: [],
  activeChunks: [],
  highlightedChunkId: null,
  isStreaming: false,

  setPapers: (papers) =>
    set({
      papers,
      selectedPaperIds: new Set(papers.filter((p) => p.status === "indexed").map((p) => p.id)),
    }),

  addPaper: (paper) => set((s) => ({ papers: [...s.papers, paper] })),
  removePaper: (id) =>
    set((s) => {
      const next = new Set(s.selectedPaperIds);
      next.delete(id);
      return { papers: s.papers.filter((p) => p.id !== id), selectedPaperIds: next };
    }),
  updatePaperStatus: (id, status) =>
    set((s) => ({ papers: s.papers.map((p) => (p.id === id ? { ...p, status } : p)) })),
  togglePaperSelection: (id) =>
    set((s) => {
      const next = new Set(s.selectedPaperIds);
      next.has(id) ? next.delete(id) : next.add(id);
      return { selectedPaperIds: next };
    }),
  selectAllPapers: () =>
    set((s) => ({ selectedPaperIds: new Set(s.papers.filter((p) => p.status === "indexed").map((p) => p.id)) })),
  deselectAllPapers: () => set({ selectedPaperIds: new Set() }),

  addMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
  updateLastAssistantMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length === 0) return { messages: msgs };
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") msgs[msgs.length - 1] = { ...last, content };
      return { messages: msgs };
    }),
  finalizeAssistantMessage: (chunks) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length === 0) return { messages: msgs, activeChunks: chunks, isStreaming: false };
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") msgs[msgs.length - 1] = { ...last, chunks, isStreaming: false };
      return { messages: msgs, activeChunks: chunks, isStreaming: false };
    }),
  clearChat: () => set({ messages: [], activeChunks: [], highlightedChunkId: null }),
  setIsStreaming: (v) => set({ isStreaming: v }),

  setActiveChunks: (chunks) => set({ activeChunks: chunks }),
  setHighlightedChunkId: (id) => set({ highlightedChunkId: id }),
}));
