import json
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.deps import get_current_user
from backend.db_chat import init_chat_table, save_message, get_history, clear_history
from rag.retriever import hybrid_retrieve
from langchain_google_genai import ChatGoogleGenerativeAI


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    paper_ids: List[str] = []
    chat_history: List[ChatMessage] = []


router = APIRouter()

load_dotenv()
init_chat_table()


def _basename(path: str) -> str:
    if not path:
        return "unknown"
    return os.path.basename(path).replace("\\", "/").split("/")[-1]



class SaveMessageRequest(BaseModel):
    id: str
    role: str
    content: str
    chunks: list = []


@router.get("/history")
async def chat_history(current_user=Depends(get_current_user)):
    return get_history(current_user["id"])


@router.delete("/history")
async def delete_chat_history(current_user=Depends(get_current_user)):
    clear_history(current_user["id"])
    return {"cleared": True}


@router.post("/save")
async def save_chat_message(request: SaveMessageRequest, current_user=Depends(get_current_user)):
    save_message(
        msg_id=request.id,
        user_id=current_user["id"],
        role=request.role,
        content=request.content,
        chunks=request.chunks if request.chunks else None,
    )
    return {"saved": True}


@router.post("")
async def chat(request: ChatRequest, current_user=Depends(get_current_user)):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not set.")

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    def generate():
        docs, meta_map = hybrid_retrieve(request.query, user_id=current_user["id"], paper_ids=request.paper_ids)

        context_lines = []
        for idx, doc in enumerate(docs, start=1):
            source_raw = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
            source = _basename(source_raw)
            paper_id = doc.metadata.get("paper_id") or "noid"
            title = doc.metadata.get("title") or source
            year = doc.metadata.get("year") or "Unknown"
            key = (doc.page_content, str(source_raw), str(paper_id))
            meta = meta_map.get(key, {})
            score = meta.get("rerank_score") or meta.get("rrf_score")
            score_str = f"{score:.3f}" if isinstance(score, float) else "n/a"
            context_lines.append(f"[{idx}] Paper: {title} ({year}) (score: {score_str})\n{doc.page_content}")

        context_block = "\n\n".join(context_lines)

        system_prompt = (
            "You are a research assistant. Answer using ONLY the Context block attached to the CURRENT question. "
            "Do NOT use information from previous messages in the conversation — the user may have changed which papers are selected. "
            "The context contains numbered excerpts from research papers, like [1], [2], etc. "
            "When you use information from a source, cite it inline using its number, e.g. [1]. "
            "You may cite multiple sources together, e.g. [1][3]. "
            "Keep information from different papers clearly attributed and do not conflate findings across papers. "
            "If the context does not contain enough information, say so explicitly."
        )

        # Only include previous user questions (not assistant responses) so the
        # LLM understands conversational flow but cannot reuse content from
        # previously-selected papers. Keep the last few for coherence.
        MAX_HISTORY_TURNS = 4
        prior_questions = [m.content for m in request.chat_history if m.role == "user"]
        prior_questions = prior_questions[-MAX_HISTORY_TURNS:]

        messages = [{"role": "system", "content": system_prompt}]
        if prior_questions:
            summary = "Previous questions in this conversation:\n" + "\n".join(
                f"- {q}" for q in prior_questions
            )
            messages.append({"role": "user", "content": summary})
            messages.append({"role": "assistant", "content": "Understood, I see the prior questions for context."})
        messages.append({
            "role": "user",
            "content": f"Question: {request.query}\n\nContext:\n{context_block}",
        })

        for chunk in llm.stream(messages):
            if chunk.content:
                yield f"event: token\ndata: {chunk.content}\n\n"

        chunks = []
        for doc in docs:
            raw_source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
            source = _basename(raw_source)
            paper_id = doc.metadata.get("paper_id") or "noid"
            key = (doc.page_content, str(raw_source), str(paper_id))
            meta = meta_map.get(key, {})
            chunks.append({
                "id": doc.metadata.get("chunk_id"),
                "content": doc.page_content,
                "title": doc.metadata.get("title") or source,
                "authors": doc.metadata.get("authors"),
                "year": doc.metadata.get("year"),
                "source_file": source,
                "bm25_rank": meta.get("bm25_rank", 0),
                "vector_rank": meta.get("vector_rank", 0),
                "rrf_score": meta.get("rrf_score", 0.0),
                "rerank_score": meta.get("rerank_score", 0.0),
            })

        metadata = {
            "chunks": chunks,
        }

        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
