import csv
from pathlib import Path

SPECIAL_SOURCES = {"experiment_records.json", "general_chat"}


def test_eval_expected_sources_exist() -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_sources = {
        path.name
        for path in (project_root / "data" / "raw_docs").iterdir()
        if path.is_file()
    }
    questions_path = project_root / "data" / "eval" / "rag_eval_questions.csv"

    with questions_path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            expected_sources = [
                item.strip()
                for item in row["expected_source"].split("|")
                if item.strip()
            ]
            assert expected_sources, row["id"]
            for source in expected_sources:
                assert source in raw_sources or source in SPECIAL_SOURCES, (row["id"], source)

