export type PaperStatus = "indexed" | "indexing" | "failed";

export interface Paper {
  id: string;
  title: string;
  authors: string;
  year: number;
  status: PaperStatus;
  filename: string;
}

export interface Citation {
  ref: string;
  sourceFile: string;
}

export interface RetrievedChunk {
  id: string;
  content: string;
  source: string;
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
  citations?: Citation[];
  chunks?: RetrievedChunk[];
  isStreaming?: boolean;
}

export interface RetrievalInfo {
  chunks: RetrievedChunk[];
  citations: Citation[];
}
