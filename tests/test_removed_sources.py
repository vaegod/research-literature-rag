from pathlib import Path

REMOVED_SOURCES = {
    "model_evaluation_metrics.md",
    "qwen_classification_experiment.md",
}


def test_removed_demo_sources_are_not_reintroduced() -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_docs = project_root / "data" / "raw_docs"
    eval_questions = project_root / "data" / "eval" / "rag_eval_questions.csv"

    for filename in REMOVED_SOURCES:
        assert not (raw_docs / filename).exists()
        assert filename not in eval_questions.read_text(encoding="utf-8")

