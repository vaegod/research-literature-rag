from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRACKED_PATTERNS = [
    ".env",
    ".venv/",
    "logs/",
    "vector_store/faiss_index/index.faiss",
    "vector_store/faiss_index/index.pkl",
    "data/processed_docs/chunks.jsonl",
    "data/eval/eval_result.csv",
]
SECRET_PATTERN = re.compile(
    (
        r"sk-[A-Za-z0-9_\-]{16,}|"
        r"(api[_-]?key|secret|token)\s*[:=]\s*['\"]?"
        r"(?!(your|test|example|xxx|os\.|settings\.|self\.|api_key\b|<))"
        r"[A-Za-z0-9_\-]{20,}"
    ),
    flags=re.IGNORECASE,
)
SCAN_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".csv", ".ps1", ".bat"}
SCAN_DIRS = {"app", "docs", "scripts", "tests", ".github", "data"}


def main() -> int:
    failures: list[str] = []
    tracked_files = _git_tracked_files()

    if tracked_files is not None:
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if pattern.endswith("/"):
                if any(path.startswith(pattern) for path in tracked_files):
                    failures.append(f"Forbidden tracked directory: {pattern}")
            elif pattern in tracked_files:
                failures.append(f"Forbidden tracked file: {pattern}")

    for path in _iter_scannable_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in SECRET_PATTERN.finditer(text):
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            failures.append(f"Potential secret in {relative}: {match.group(0)[:40]}")

    if failures:
        print("Open source audit failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    if tracked_files is None:
        print("Open source audit passed. Git metadata not found; tracked-file checks were skipped.")
    else:
        print("Open source audit passed.")
    return 0


def _git_tracked_files() -> set[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def _iter_scannable_files():
    for root in SCAN_DIRS:
        base = PROJECT_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if "__pycache__" in path.parts:
                continue
            yield path


if __name__ == "__main__":
    raise SystemExit(main())
