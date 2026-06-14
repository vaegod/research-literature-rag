from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.workflow import run_agent

QUESTIONS = [
    "知识蒸馏的核心思想是什么？",
    "对比 LoRA 和知识蒸馏的区别。",
    "查询 EXP-003 的实验结果。",
    "帮我生成 RAG 应用开发笔记的阅读笔记。",
]


def main() -> None:
    for question in QUESTIONS:
        print("=" * 80)
        print(f"Q: {question}")
        result = run_agent(question)
        print(f"Intent: {result.get('intent')}")
        print(result.get("answer", ""))


if __name__ == "__main__":
    main()
