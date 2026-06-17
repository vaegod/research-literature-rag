import json
from dataclasses import replace

from app.config import get_settings
from app.retriever.loaders import load_single_document
from app.retriever.mineru_client import _cache_dir, parse_pdf_with_mineru


def test_load_markdown_document(tmp_path) -> None:
    path = tmp_path / "paper_note.md"
    path.write_text("# Title\n\n知识蒸馏使用教师模型指导学生模型。", encoding="utf-8")

    docs = load_single_document(path)

    assert len(docs) == 1
    assert "知识蒸馏" in docs[0].page_content
    assert docs[0].metadata["source"] == "paper_note.md"
    assert docs[0].metadata["page"] == 1


def test_mineru_cached_content_list_to_page_documents(tmp_path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf bytes for cache hash")
    settings = replace(
        get_settings(),
        mineru_api_token="token",
        mineru_cache_path=tmp_path / "mineru_cache",
        mineru_model_version="vlm",
    )
    cache_dir = _cache_dir(pdf_path, settings)
    cache_dir.mkdir(parents=True)
    (cache_dir / "paper_content_list.json").write_text(
        json.dumps(
            [
                {"type": "text", "text": "Abstract", "text_level": 1, "page_idx": 0},
                {"type": "text", "text": "This paper studies RAG.", "page_idx": 0},
                {"type": "list", "list_items": ["Contribution one", "Contribution two"], "page_idx": 0},
                {"type": "code", "code_body": "print('mineru')", "page_idx": 0},
                {"type": "table", "table_body": "| Metric | Value |\n| --- | --- |\n| EM | 80 |", "page_idx": 1},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    docs = parse_pdf_with_mineru(pdf_path, settings)

    assert len(docs) == 2
    assert "# Abstract" in docs[0].page_content
    assert "This paper studies RAG." in docs[0].page_content
    assert "- Contribution one" in docs[0].page_content
    assert "print('mineru')" in docs[0].page_content
    assert "| Metric | Value |" in docs[1].page_content
    assert docs[0].metadata["source"] == "paper.pdf"
    assert docs[0].metadata["page"] == 1
    assert docs[1].metadata["page"] == 2
    assert docs[0].metadata["parser"] == "mineru"
