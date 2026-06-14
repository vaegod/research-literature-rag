from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


def safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", name, flags=re.UNICODE)
    return name or "uploaded_document.txt"


def validate_supported_file(filename: str) -> None:
    if not filename:
        raise ValueError("Missing filename.")
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type: {suffix}. Allowed: {allowed}")


async def save_upload_file(
    upload_file: UploadFile,
    target_dir: Path,
    max_size_bytes: int | None = None,
) -> tuple[Path, int]:
    filename = upload_file.filename or ""
    validate_supported_file(filename)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(filename)
    target_path = _available_path(target_dir / filename)
    content = await upload_file.read()
    if not content:
        raise ValueError("Uploaded file is empty.")
    if max_size_bytes is not None and len(content) > max_size_bytes:
        size_mb = max_size_bytes / 1024 / 1024
        raise ValueError(f"Uploaded file is too large. Max size is {size_mb:.0f} MB.")
    target_path.write_bytes(content)
    return target_path, len(content)


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
