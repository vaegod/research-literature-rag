from __future__ import annotations

import re
from pathlib import Path

from app.config import get_settings
from app.retriever.loaders import Document


def _slug(value: str) -> str:
    value = Path(value).stem.lower()
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "_", value, flags=re.UNICODE).strip("_")
    return value or "document"


SECTION_PATTERNS: list[tuple[str, str]] = [
    ("references", r"(?im)^\s*(references|bibliography)\s*$"),
    ("limitations", r"(?im)^\s*(limitations?|discussion)\s*$"),
    ("conclusion", r"(?im)^\s*(conclusions?|结论)\s*$"),
    ("experiments", r"(?im)^\s*(experiments?|experimental setup|results?|evaluation|实验|实验结果)\s*$"),
    ("method", r"(?im)^\s*(methodology|methods?|approach|framework|model|方法|模型)\s*$"),
    ("introduction", r"(?im)^\s*(introduction|引言)\s*$"),
    ("abstract", r"(?im)^\s*(abstract|摘要)\s*$"),
]

INLINE_SECTION_HINTS: list[tuple[str, str]] = [
    ("abstract", r"\babstract\b|摘要"),
    ("introduction", r"\bintroduction\b|引言|main contributions?|contributions?"),
    ("method", r"\bmethod\b|\bapproach\b|\bframework\b|方法|模型"),
    ("experiments", r"\bexperiment\b|\bresults?\b|\bevaluation\b|实验|评测|结果"),
    ("conclusion", r"\bconclusion\b|结论"),
    ("limitations", r"\blimitation\b|\bdiscussion\b|局限"),
    ("references", r"\breferences\b|\bbibliography\b|参考文献"),
]


def split_documents(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    settings = get_settings()
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", "。", "，", " ", ""],
        )
        chunks = splitter.split_documents(documents)
    except Exception:
        chunks = _fallback_split(documents, chunk_size, chunk_overlap)

    counters: dict[str, int] = {}
    section_state: dict[str, str] = {}
    for chunk in chunks:
        source = chunk.metadata.get("source", "document")
        doc_id = _slug(source)
        counters[doc_id] = counters.get(doc_id, 0) + 1
        inferred_section = _infer_section(chunk.page_content)
        if inferred_section != "body":
            section_state[doc_id] = inferred_section
        section = section_state.get(doc_id, inferred_section)
        chunk.metadata.update(
            {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_chunk_{counters[doc_id]:04d}",
                "section": section,
            }
        )
    return chunks


def _infer_section(text: str) -> str:
    preview = text[:1800]
    for section, pattern in SECTION_PATTERNS:
        if re.search(pattern, preview):
            return section
    lowered = preview.lower()
    for section, pattern in INLINE_SECTION_HINTS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return section
    return "body"


def _fallback_split(
    documents: list[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    chunks: list[Document] = []
    step = max(chunk_size - chunk_overlap, 1)
    for doc in documents:
        text = doc.page_content
        for start in range(0, len(text), step):
            piece = text[start : start + chunk_size].strip()
            if not piece:
                continue
            chunks.append(Document(page_content=piece, metadata=dict(doc.metadata)))
    return chunks
