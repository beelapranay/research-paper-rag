export type PaperStatus = "indexed" | "indexing" | "processing" | "failed";

export interface Paper {
  id: string;
  title: string;
  authors: string;
  year: number;
  status: PaperStatus;
  filename: string;
}

export interface RetrievedChunk {
  id: string;
  content: string;
  source: string;
  title?: string;
  authors: string;
  year: number;
  bm25Rank: number;
  vectorRank: number;
  rrfScore: number;
  rerankScore: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  chunks?: RetrievedChunk[];
  isStreaming?: boolean;
}

export interface RetrievalInfo {
  chunks: RetrievedChunk[];
}
