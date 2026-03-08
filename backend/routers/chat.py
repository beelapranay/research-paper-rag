import json
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.deps import get_current_user
from rag.retriever import hybrid_retrieve
from langchain_groq import ChatGroq


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    paper_ids: List[str] = []
    chat_history: List[ChatMessage] = []


router = APIRouter()

load_dotenv()


@router.post("")
async def chat(request: ChatRequest, current_user=Depends(get_current_user)):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set.")

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=api_key)

    def generate():
        # 1. Retrieve + rerank (currently ignores paper_ids; will add filtering later)
        docs, scores = hybrid_retrieve(request.query)

        # 2. Build context text
        context_lines = []
        for doc in docs:
            source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
            authors = doc.metadata.get("authors") or "Unknown"
            year = doc.metadata.get("year") or "Unknown"
            key = (doc.page_content, str(source))
            score = scores.get(key)
            score_str = f"{score:.3f}" if isinstance(score, float) else "n/a"
            label = f"[{authors}, {year}]"
            context_lines.append(f"{label} (score: {score_str})\n{doc.page_content}")

        context_block = "\n\n".join(context_lines)

        system_prompt = (
            "You are a research assistant. Answer using ONLY the provided context. "
            "For every claim you make, cite the source using this format: [Author et al., Year]. "
            "If the context does not contain enough information, say so explicitly. "
            "Do not fabricate citations or facts."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for m in request.chat_history:
            messages.append({"role": m.role, "content": m.content})
        messages.append({
            "role": "user",
            "content": f"Question: {request.query}\n\nContext:\n{context_block}",
        })

        # 3. Stream tokens
        for chunk in llm.stream(messages):
            if chunk.content:
                yield f"event: token\ndata: {chunk.content}\n\n"

        # 4. Emit metadata
        chunks = []
        for doc in docs:
            source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
            chunks.append({
                "content": doc.page_content,
                "title": doc.metadata.get("title"),
                "authors": doc.metadata.get("authors"),
                "year": doc.metadata.get("year"),
                "source_file": source,
                "bm25_rank": 0,
                "vector_rank": 0,
                "rrf_score": 0.0,
                "rerank_score": 0.0,
            })

        metadata = {
            "citations": [],
            "chunks": chunks,
        }

        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
