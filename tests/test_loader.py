from app.retriever.loaders import load_single_document


def test_load_markdown_document(tmp_path) -> None:
    path = tmp_path / "paper_note.md"
    path.write_text("# Title\n\n知识蒸馏使用教师模型指导学生模型。", encoding="utf-8")

    docs = load_single_document(path)

    assert len(docs) == 1
    assert "知识蒸馏" in docs[0].page_content
    assert docs[0].metadata["source"] == "paper_note.md"
    assert docs[0].metadata["page"] == 1
