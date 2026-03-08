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
  addPaper: (paper: Paper) => void;
  removePaper: (id: string) => void;
  updatePaperStatus: (id: string, status: Paper["status"]) => void;
  togglePaperSelection: (id: string) => void;
  selectAllPapers: () => void;
  deselectAllPapers: () => void;

  // Chat actions
  addMessage: (message: Message) => void;
  updateLastAssistantMessage: (content: string) => void;
  finalizeAssistantMessage: (citations: Message["citations"], chunks: RetrievedChunk[]) => void;
  clearChat: () => void;
  setIsStreaming: (v: boolean) => void;

  // Retrieval actions
  setActiveChunks: (chunks: RetrievedChunk[]) => void;
  setHighlightedChunkId: (id: string | null) => void;
}

// Mock papers for demo
const mockPapers: Paper[] = [
  { id: "1", title: "Attention Is All You Need", authors: "Vaswani et al.", year: 2017, status: "indexed", filename: "attention.pdf" },
  { id: "2", title: "BERT: Pre-training of Deep Bidirectional Transformers", authors: "Devlin et al.", year: 2019, status: "indexed", filename: "bert.pdf" },
  { id: "3", title: "Language Models are Few-Shot Learners", authors: "Brown et al.", year: 2020, status: "indexed", filename: "gpt3.pdf" },
  { id: "4", title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP", authors: "Lewis et al.", year: 2020, status: "indexing", filename: "rag.pdf" },
  { id: "5", title: "Constitutional AI: Harmlessness from AI Feedback", authors: "Bai et al.", year: 2022, status: "indexed", filename: "constitutional.pdf" },
];

const mockChunks: RetrievedChunk[] = [
  {
    id: "c1",
    content: "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism.",
    source: "attention.pdf",
    authors: "Vaswani et al.",
    year: 2017,
    bm25Rank: 3,
    vectorRank: 1,
    rrfScore: 0.048,
    rerankScore: 0.94,
  },
  {
    id: "c2",
    content: "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments show these models to be superior in quality while being more parallelizable.",
    source: "attention.pdf",
    authors: "Vaswani et al.",
    year: 2017,
    bm25Rank: 1,
    vectorRank: 2,
    rrfScore: 0.045,
    rerankScore: 0.91,
  },
  {
    id: "c3",
    content: "BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers. The pre-trained BERT model can be fine-tuned with just one additional output layer.",
    source: "bert.pdf",
    authors: "Devlin et al.",
    year: 2019,
    bm25Rank: 2,
    vectorRank: 4,
    rrfScore: 0.038,
    rerankScore: 0.82,
  },
  {
    id: "c4",
    content: "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. We show that scaling up language models greatly improves task-agnostic, few-shot performance.",
    source: "gpt3.pdf",
    authors: "Brown et al.",
    year: 2020,
    bm25Rank: 5,
    vectorRank: 3,
    rrfScore: 0.031,
    rerankScore: 0.73,
  },
  {
    id: "c5",
    content: "While pre-trained language models have been shown to store factual knowledge in their parameters, their ability to access and precisely manipulate that knowledge is still limited. RAG models combine pre-trained parametric and non-parametric memory.",
    source: "rag.pdf",
    authors: "Lewis et al.",
    year: 2020,
    bm25Rank: 4,
    vectorRank: 5,
    rrfScore: 0.027,
    rerankScore: 0.65,
  },
];

const mockMessages: Message[] = [
  {
    id: "m1",
    role: "user",
    content: "How do Transformers differ from previous sequence models?",
  },
  {
    id: "m2",
    role: "assistant",
    content: "Transformers represent a fundamental departure from previous sequence transduction models. Unlike RNNs and CNNs that process sequences step-by-step, the Transformer architecture relies **entirely on attention mechanisms** [Vaswani et al., 2017], dispensing with recurrence and convolutions altogether.\n\nThe key advantages include:\n\n1. **Parallelization** — Since there's no sequential dependency, all positions can be processed simultaneously\n2. **Long-range dependencies** — Self-attention connects all positions directly, unlike RNNs where information must flow through many steps\n3. **Scalability** — This architecture enabled massive scaling, leading to models like BERT [Devlin et al., 2019] and GPT-3 [Brown et al., 2020]\n\nBERT extended this by introducing bidirectional pre-training, conditioning on both left and right context simultaneously. GPT-3 then demonstrated that simply scaling up transformer-based language models leads to remarkable few-shot learning capabilities.",
    citations: [
      { ref: "Vaswani et al., 2017", sourceFile: "attention.pdf" },
      { ref: "Devlin et al., 2019", sourceFile: "bert.pdf" },
      { ref: "Brown et al., 2020", sourceFile: "gpt3.pdf" },
    ],
    chunks: mockChunks,
  },
];

export const useAppStore = create<AppState>((set, get) => ({
  papers: mockPapers,
  selectedPaperIds: new Set(mockPapers.filter((p) => p.status === "indexed").map((p) => p.id)),
  messages: mockMessages,
  activeChunks: mockChunks,
  highlightedChunkId: null,
  isStreaming: false,

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
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") msgs[msgs.length - 1] = { ...last, content };
      return { messages: msgs };
    }),
  finalizeAssistantMessage: (citations, chunks) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") msgs[msgs.length - 1] = { ...last, citations, chunks, isStreaming: false };
      return { messages: msgs, activeChunks: chunks, isStreaming: false };
    }),
  clearChat: () => set({ messages: [], activeChunks: [], highlightedChunkId: null }),
  setIsStreaming: (v) => set({ isStreaming: v }),

  setActiveChunks: (chunks) => set({ activeChunks: chunks }),
  setHighlightedChunkId: (id) => set({ highlightedChunkId: id }),
}));
