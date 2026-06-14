from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.eval_service import run_eval


def main() -> None:
    parser = ArgumentParser(description="Run RAG evaluation.")
    parser.add_argument("--limit", type=int, default=None, help="Only evaluate the first N cases.")
    args = parser.parse_args()

    report = run_eval(limit=args.limit)
    print(f"Total questions: {report.total}")
    print(f"Source hit rate: {report.source_hit_rate:.2%}")
    print(f"Keyword hit rate: {report.keyword_hit_rate:.2%}")
    print(f"Average latency: {report.avg_latency:.2f}s")
    print(f"Failed cases: {len(report.failed_cases)}")
    for case in report.failed_cases[:5]:
        print(f"- {case.id} [{case.intent}] {case.question}: {case.answer_preview}")


if __name__ == "__main__":
    main()
