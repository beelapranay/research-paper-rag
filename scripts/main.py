from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from rag.tools import retrieve_info
import os
import re
from rag.output_parser import parse_response

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

system_prompt = (
    "You are a research assistant. Answer using ONLY the provided context. "
    "For every claim you make, cite the source using this format: [Author et al., Year]. "
    "If the context does not contain enough information, say so explicitly. "
    "Do not fabricate citations or facts."
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

    def _citation_label(authors: str | None, year: str | None, fallback_source: str) -> str:
        author_label = "Unknown"
        if authors and authors.strip() and authors.strip().lower() != "unknown":
            if "," in authors:
                author_label = authors.split(",", 1)[0].strip()
            elif " and " in authors:
                author_label = authors.split(" and ", 1)[0].strip()
            else:
                author_label = authors.strip()
            if (" and " in authors) or ("," in authors):
                author_label = f"{author_label} et al."

        year_label = year if year and year.strip() else "Unknown"
        if author_label == "Unknown":
            base = os.path.splitext(os.path.basename(fallback_source))[0] if fallback_source else "Unknown"
            author_label = base or "Unknown"

        return f"[{author_label}, {year_label}]"

    def _format_context(chunks: list[dict]) -> str:
        lines = []
        for chunk in chunks:
            label = _citation_label(
                authors=chunk.get("authors"),
                year=chunk.get("year"),
                fallback_source=chunk.get("source") or "unknown",
            )
            score = chunk.get("score")
            score_str = f"{score:.2f}" if isinstance(score, float) else "n/a"
            content = chunk.get("content", "")
            lines.append(f"{label} (score: {score_str})\n{content}")
        return "\n\n".join(lines)

    def _citations_valid(answer: str) -> bool:
        sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
        if not sentences:
            return False
        pattern = re.compile(r"\[[^\]]+?,\s*\d{4}\]")
        for sent in sentences:
            if not sent.strip():
                continue
            if not any(ch.isalnum() for ch in sent):
                continue
            if not pattern.search(sent):
                return False
        return True

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

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print()

    if not _citations_valid(full_response):
        reprompt = {
            "role": "user",
            "content": (
                "You must cite sources for every sentence using [Author et al., Year]. "
                "Re-answer the question using ONLY the provided context."
            ),
        }
        messages_retry = [
            {"role": "system", "content": system_prompt},
            *chat_history,
            user_message,
            reprompt,
        ]
        print("Assistant: ", end="", flush=True)
        full_response = ""
        for chunk in llm.stream(messages_retry):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                full_response += chunk.content
        print()

    rag_response, citations_ok = parse_response(full_response, context)
    if not citations_ok:
        reprompt = {
            "role": "user",
            "content": (
                "Some citations do not match the provided context. "
                "Re-answer using ONLY citations that appear in the context block."
            ),
        }
        messages_retry = [
            {"role": "system", "content": system_prompt},
            *chat_history,
            user_message,
            reprompt,
        ]
        print("Assistant: ", end="", flush=True)
        full_response = ""
        for chunk in llm.stream(messages_retry):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                full_response += chunk.content
        print()
        rag_response, citations_ok = parse_response(full_response, context)

    chat_history.append(user_message)
    chat_history.append({"role": "assistant", "content": full_response})
