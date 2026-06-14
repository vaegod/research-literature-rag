from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import get_settings


def load_experiment_records(path: Path | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    path = path or settings.experiment_records_path
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def search_experiments(query: str) -> list[dict[str, Any]]:
    records = load_experiment_records()
    normalized = query.lower()
    exp_ids = [item.upper() for item in re.findall(r"exp-\d+", query, flags=re.IGNORECASE)]

    matches: list[dict[str, Any]] = []
    for record in records:
        record_text = json.dumps(record, ensure_ascii=False).lower()
        record_id = str(record.get("experiment_id", "")).upper()
        if exp_ids and record_id in exp_ids:
            matches.append(record)
            continue
        if not exp_ids and any(token for token in normalized.split() if token and token in record_text):
            matches.append(record)
            continue
        if not exp_ids and normalized in record_text:
            matches.append(record)

    return matches


def format_experiment_answer(query: str, records: list[dict[str, Any]]) -> str:
    if not records:
        return f"没有查询到与“{query}”匹配的实验记录。"

    lines = [f"共查询到 {len(records)} 条实验记录："]
    for record in records:
        metric = record.get("metric", {})
        metric_text = "，".join(f"{key}={value}" for key, value in metric.items()) or "未记录"
        lines.extend(
            [
                "",
                f"- 实验编号：{record.get('experiment_id', '未知')}",
                f"  - 任务：{record.get('task', '未记录')}",
                f"  - 数据集：{record.get('dataset', '未记录')}",
                f"  - 教师模型：{record.get('teacher_model', '未记录')}",
                f"  - 学生模型：{record.get('student_model', '未记录')}",
                f"  - 方法：{record.get('method', '未记录')}",
                f"  - 指标：{metric_text}",
                f"  - 结论：{record.get('conclusion', '未记录')}",
            ]
        )
    return "\n".join(lines)


def run_experiment_query(query: str) -> dict[str, Any]:
    records = search_experiments(query)
    return {
        "answer": format_experiment_answer(query, records),
        "records": records,
        "total": len(records),
    }
