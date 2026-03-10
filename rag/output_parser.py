# output_parser.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Citation:
    ref: str
    source_file: str


@dataclass
class RAGResponse:
    answer: str
    citations: List[Citation]


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
        base = fallback_source.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        base = base.rsplit(".", 1)[0]
        author_label = base or "Unknown"

    return f"[{author_label}, {year_label}]"


def _build_allowed_refs(chunks: List[dict]) -> Dict[str, str]:
    allowed: Dict[str, str] = {}
    for chunk in chunks:
        label = _citation_label(
            authors=chunk.get("authors"),
            year=chunk.get("year"),
            fallback_source=chunk.get("source") or "unknown",
        )
        source = chunk.get("source") or "unknown"
        allowed[label] = source
    return allowed


def parse_response(answer: str, context_chunks: List[dict]) -> Tuple[RAGResponse, bool]:
    allowed = _build_allowed_refs(context_chunks)
    pattern = re.compile(r"\[[^\]]+?,\s*\d{4}[a-z]?\]")
    refs = pattern.findall(answer)

    citations: List[Citation] = []
    all_valid = True
    for ref in refs:
        source = allowed.get(ref)
        if not source:
            all_valid = False
            continue
        citations.append(Citation(ref=ref, source_file=source))

    return RAGResponse(answer=answer, citations=citations), all_valid
