from dataclasses import replace

from app.config import get_settings
from app.models.schemas import SearchResult
from app.services import eval_service


def test_run_eval_records_case_errors(tmp_path, monkeypatch) -> None:
    questions_path = tmp_path / "questions.csv"
    questions_path.write_text(
        "\n".join(
            [
                "id,question,expected_source,expected_keywords,intent",
                "1,知识蒸馏是什么,knowledge_distillation_survey.md,教师模型,literature_qa",
            ]
        ),
        encoding="utf-8",
    )
    settings = replace(
        get_settings(),
        eval_questions_path=questions_path,
        eval_result_path=tmp_path / "eval_result.csv",
    )

    def fake_run_agent(question: str):
        raise RuntimeError("provider down")

    monkeypatch.setattr(eval_service, "run_agent", fake_run_agent)

    report = eval_service.run_eval(settings=settings)

    assert report.total == 1
    assert report.source_hit_rate == 0
    assert report.keyword_hit_rate == 0
    assert "RuntimeError: provider down" in report.failed_cases[0].answer_preview
    assert settings.eval_result_path.exists()


def test_run_eval_calculates_retrieval_metrics(tmp_path, monkeypatch) -> None:
    questions_path = tmp_path / "questions.csv"
    questions_path.write_text(
        "\n".join(
            [
                "id,question,expected_source,expected_keywords,intent,expected_chunk_ids",
                (
                    "1,RAG 流程是什么,rag_for_llm_applications.md,"
                    "文档解析;检索,literature_qa,rag_for_llm_applications_chunk_0001"
                ),
            ]
        ),
        encoding="utf-8",
    )
    settings = replace(
        get_settings(),
        eval_questions_path=questions_path,
        eval_result_path=tmp_path / "eval_result.csv",
    )

    def fake_run_agent(question: str):
        return {
            "answer": "RAG 包含文档解析和检索。",
            "sources": ["rag_for_llm_applications.md"],
            "related_chunks": [
                SearchResult(
                    content="RAG chunk",
                    source="rag_for_llm_applications.md",
                    page=1,
                    score=1.0,
                    metadata={"chunk_id": "rag_for_llm_applications_chunk_0001"},
                )
            ],
        }

    monkeypatch.setattr(eval_service, "run_agent", fake_run_agent)

    report = eval_service.run_eval(settings=settings)

    assert report.source_hit_rate == 1
    assert report.keyword_hit_rate == 1
    assert report.retrieval_recall_at_k == 1
    assert report.mean_reciprocal_rank == 1
    assert report.failed_cases == []
