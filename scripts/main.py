from dotenv import load_dotenv
load_dotenv()

import re
from langchain_google_genai import ChatGoogleGenerativeAI
from rag.tools import retrieve_info

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

system_prompt = (
    "You are a research assistant. Answer using ONLY the provided context. "
    "Do not include citations or bracketed references in your response. "
    "If the context does not contain enough information, say so explicitly."
)

FOLLOW_UP_HINTS = {
    "tell me more",
    "more",
    "go on",
    "continue",
    "elaborate",
    "yep",
    "yes",
    "smth like that",
    "something like that",
}


def is_vague_follow_up(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized in FOLLOW_UP_HINTS:
        return True
    prefixes = (
        "yep", "yes", "yeah", "ok", "okay", "sure",
        "continue", "go on", "tell me more", "more", "elaborate",
    )
    return any(normalized.startswith(prefix) for prefix in prefixes)


def is_ingestion_topic(text: str) -> bool:
    normalized = text.strip().lower()
    keywords = ("ingest", "indexed", "index", "source", "url", "loaded")
    return any(keyword in normalized for keyword in keywords)


def _looks_like_citation(text: str) -> bool:
    if "Unknown" in text:
        return True
    return re.search(r"\b(19|20)\d{2}\b", text) is not None


def _strip_citations_stream(text: str, state: dict) -> str:
    output = []
    for ch in text:
        if not state["in_bracket"]:
            if ch == "[":
                state["in_bracket"] = True
                state["buffer"] = "["
            else:
                output.append(ch)
        else:
            state["buffer"] += ch
            if ch == "]":
                buf = state["buffer"]
                if not _looks_like_citation(buf):
                    output.append(buf)
                state["in_bracket"] = False
                state["buffer"] = ""
    return "".join(output)


print("--- Gemini RAG CLI Ready ---")
print("Type 'exit' to quit.")

last_topic_query = ""
chat_history = []  # Persists across turns

while True:
    try:
        user_input = input("\n> ").strip()
    except EOFError:
        break

    if not user_input:
        continue
    if user_input.lower() in {"exit", "quit"}:
        break

    follow_up = is_vague_follow_up(user_input)

    retrieval_query = user_input
    if follow_up and last_topic_query:
        retrieval_query = f"{last_topic_query}\n\nFollow-up: {user_input}"
    elif not follow_up:
        last_topic_query = user_input

    if follow_up and last_topic_query and is_ingestion_topic(last_topic_query):
        context = retrieve_info.invoke(last_topic_query)
        if isinstance(context, str) and context.startswith("Ingested sources:"):
            print(f"\nAssistant: {context}")
            continue

    model_question = user_input
    if follow_up and last_topic_query:
        model_question = f"{user_input} (Follow-up about: {last_topic_query})"

    # Step 1: Retrieval
    context = retrieve_info.invoke(retrieval_query)

    if not context:
        print("No relevant context found in your documents.")
        continue

    if isinstance(context, str) and context.startswith("Ingested sources:"):
        print(f"\nAssistant: {context}")
        continue

    if not isinstance(context, list):
        print("No relevant context found in your documents.")
        continue

    def _format_context(chunks: list[dict]) -> str:
        lines = []
        for chunk in chunks:
            title = chunk.get("title") or chunk.get("source") or "Unknown"
            year = chunk.get("year") or "Unknown"
            score = chunk.get("score")
            score_str = f"{score:.2f}" if isinstance(score, float) else "n/a"
            content = chunk.get("content", "")
            lines.append(f"[{title}, {year}] (score: {score_str})\n{content}")
        return "\n\n".join(lines)

    formatted_context = _format_context(context)

    user_message = {
        "role": "user",
        "content": f"Question: {model_question}\n\nContext:\n{formatted_context}",
    }

    messages = [
        {"role": "system", "content": system_prompt},
        *chat_history,
        user_message,
    ]

    print("\nAssistant: ", end="", flush=True)
    full_response = ""
    strip_state = {"in_bracket": False, "buffer": ""}

    for chunk in llm.stream(messages):
        if chunk.content:
            cleaned = _strip_citations_stream(chunk.content, strip_state)
            if cleaned:
                print(cleaned, end="", flush=True)
                full_response += cleaned

    if strip_state["buffer"]:
        print(strip_state["buffer"], end="", flush=True)
        full_response += strip_state["buffer"]

    print()

    chat_history.append(user_message)
    chat_history.append({"role": "assistant", "content": full_response})
