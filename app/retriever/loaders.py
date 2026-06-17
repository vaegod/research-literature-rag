from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.retriever.mineru_client import MinerUError, parse_pdf_with_mineru
from app.utils.file_utils import SUPPORTED_EXTENSIONS
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover - used only when LangChain is unavailable.

    @dataclass
    class Document:  # type: ignore[no-redef]
        page_content: str
        metadata: dict


def _doc_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    return "text"


def load_single_document(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return []

    if suffix == ".pdf":
        return _load_pdf(path)

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return []

    return [
        Document(
            page_content=text,
            metadata={
                "source": path.name,
                "source_path": str(path),
                "file_type": _doc_type(path),
                "page": 1,
            },
        )
    ]


def _load_pdf(path: Path) -> list[Document]:
    settings = get_settings()
    if settings.mineru_parser_enabled:
        try:
            return parse_pdf_with_mineru(path, settings)
        except MinerUError:
            if not settings.mineru_fallback_to_pypdf:
                raise
            logger.exception("MinerU parsing failed for %s; falling back to pypdf.", path)

    return _load_pdf_with_pypdf(path)


def _load_pdf_with_pypdf(path: Path) -> list[Document]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    docs: list[Document] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": path.name,
                    "source_path": str(path),
                    "file_type": "pdf",
                    "page": page_number,
                },
            )
        )
    return docs


def load_documents(raw_docs_path: Path) -> list[Document]:
    if not raw_docs_path.exists():
        return []

    documents: list[Document] = []
    for path in sorted(raw_docs_path.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.extend(load_single_document(path))
    return documents
