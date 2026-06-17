from __future__ import annotations

import hashlib
import json
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover - used only when LangChain is unavailable.

    @dataclass
    class Document:  # type: ignore[no-redef]
        page_content: str
        metadata: dict[str, Any]


class MinerUError(RuntimeError):
    """Raised when the MinerU API cannot return a parsed document."""


def parse_pdf_with_mineru(path: Path, settings: Settings) -> list[Document]:
    if not settings.mineru_api_token:
        raise MinerUError("MINERU_API_TOKEN is required when MINERU_PARSER_ENABLED=true.")

    cache_dir = _cache_dir(path, settings)
    cached_docs = _load_from_cache(path, cache_dir, settings)
    if cached_docs:
        return cached_docs

    cache_dir.mkdir(parents=True, exist_ok=True)
    with MinerUClient(settings) as client:
        result_zip_url = client.parse_pdf(path)
        _download_and_extract_zip(result_zip_url, cache_dir)

    docs = _load_from_cache(path, cache_dir, settings)
    if not docs:
        raise MinerUError(f"MinerU result did not contain readable Markdown for {path.name}.")
    return docs


@dataclass
class MinerUClient:
    settings: Settings

    def __post_init__(self) -> None:
        self.http = httpx.Client(
            base_url=self.settings.mineru_api_base_url,
            timeout=httpx.Timeout(60.0, read=120.0),
            headers={"Authorization": f"Bearer {self.settings.mineru_api_token}"},
            follow_redirects=True,
        )

    def __enter__(self) -> MinerUClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.http.close()

    def parse_pdf(self, path: Path) -> str:
        upload_url, batch_id = self._create_upload_url(path)
        with path.open("rb") as file:
            upload_response = httpx.put(
                upload_url,
                content=file,
                follow_redirects=True,
                timeout=httpx.Timeout(60.0, read=120.0),
            )
        upload_response.raise_for_status()
        return self._wait_for_result(batch_id)

    def _create_upload_url(self, path: Path) -> tuple[str, str]:
        payload = {
            "enable_formula": self.settings.mineru_enable_formula,
            "enable_table": self.settings.mineru_enable_table,
            "language": self.settings.mineru_language,
            "model_version": self.settings.mineru_model_version,
            "files": [
                {
                    "name": path.name,
                    "is_ocr": self.settings.mineru_enable_ocr,
                    "data_id": f"{path.stem}-{_sha256(path)[:12]}",
                }
            ],
        }
        response = self.http.post("/api/v4/file-urls/batch", json=payload)
        response.raise_for_status()
        body = response.json()
        _assert_mineru_success(body)
        data = body.get("data") or {}
        upload_urls = data.get("file_urls") or []
        batch_id = data.get("batch_id")
        if not upload_urls or not batch_id:
            raise MinerUError(f"MinerU did not return upload URL or batch_id: {body}")
        return str(upload_urls[0]), str(batch_id)

    def _wait_for_result(self, batch_id: str) -> str:
        deadline = time.monotonic() + self.settings.mineru_timeout_seconds
        last_state = ""
        while time.monotonic() < deadline:
            response = self.http.get(f"/api/v4/extract-results/batch/{batch_id}")
            response.raise_for_status()
            body = response.json()
            _assert_mineru_success(body)
            extract_result = _first_extract_result(body)
            state = str(extract_result.get("state") or extract_result.get("status") or "")
            last_state = state or last_state
            full_zip_url = extract_result.get("full_zip_url")
            if full_zip_url:
                return str(full_zip_url)
            if state.lower() in {"failed", "fail", "error"}:
                message = extract_result.get("err_msg") or extract_result.get("message") or body
                raise MinerUError(f"MinerU parse failed: {message}")
            time.sleep(max(self.settings.mineru_poll_interval_seconds, 1.0))
        raise MinerUError(f"Timed out waiting for MinerU batch {batch_id}; last state={last_state}.")


def _assert_mineru_success(body: dict[str, Any]) -> None:
    code = body.get("code")
    if code not in (None, 0, "0"):
        message = body.get("msg") or body.get("message") or body
        raise MinerUError(f"MinerU API error: {message}")


def _first_extract_result(body: dict[str, Any]) -> dict[str, Any]:
    data = body.get("data") or {}
    extract_results = data.get("extract_result") or data.get("extract_results") or []
    if isinstance(extract_results, list) and extract_results:
        result = extract_results[0]
        if isinstance(result, dict):
            return result
    if isinstance(data, dict):
        return data
    raise MinerUError(f"MinerU result is empty: {body}")


def _download_and_extract_zip(url: str, target_dir: Path) -> None:
    response = httpx.get(url, follow_redirects=True, timeout=httpx.Timeout(60.0, read=120.0))
    response.raise_for_status()
    zip_path = target_dir / "mineru_result.zip"
    zip_path.write_bytes(response.content)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (target_dir / member.filename).resolve()
            try:
                target.relative_to(target_dir.resolve())
            except ValueError as exc:
                raise MinerUError(f"Unsafe file path in MinerU zip: {member.filename}") from exc
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))


def _load_from_cache(path: Path, cache_dir: Path, settings: Settings) -> list[Document]:
    content_list_path = _find_first(cache_dir, "*content_list*.json")
    if content_list_path:
        docs = _documents_from_content_list(path, content_list_path, settings)
        if docs:
            return docs

    markdown_path = _find_first(cache_dir, "*full.md") or _find_first(cache_dir, "*.md")
    if markdown_path:
        text = markdown_path.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            return [
                Document(
                    page_content=text,
                    metadata=_metadata(path, settings, page=1, mineru_source=str(markdown_path)),
                )
            ]
    return []


def _documents_from_content_list(
    source_path: Path,
    content_list_path: Path,
    settings: Settings,
) -> list[Document]:
    try:
        data = json.loads(content_list_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    pages = _page_blocks(data)
    docs: list[Document] = []
    for page_index in sorted(pages):
        text = "\n\n".join(
            block_text
            for block in pages[page_index]
            if (block_text := _block_to_markdown(block))
        ).strip()
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata=_metadata(
                    source_path,
                    settings,
                    page=page_index + 1,
                    mineru_source=str(content_list_path),
                ),
            )
        )
    return docs


def _page_blocks(data: Any) -> dict[int, list[Any]]:
    pages: dict[int, list[Any]] = defaultdict(list)
    if isinstance(data, list) and data and all(isinstance(item, list) for item in data):
        for page_index, blocks in enumerate(data):
            pages[page_index].extend(blocks)
        return pages

    if isinstance(data, list):
        for block in data:
            if not isinstance(block, dict):
                continue
            page_index = _as_int(block.get("page_idx") or block.get("page") or 0)
            pages[max(page_index, 0)].append(block)
    return pages


def _block_to_markdown(block: Any) -> str:
    if not isinstance(block, dict):
        return _normalize_text(str(block))

    block_type = str(block.get("type") or "").lower()
    if block_type in {"header", "footer", "page_number", "page-header", "page-footer"}:
        return ""

    text = _extract_block_text(block)
    if not text:
        return ""

    if block_type in {"title", "text"}:
        level = _as_int(block.get("text_level") or block.get("level") or 0)
        if level > 0:
            return f"{'#' * min(level, 6)} {text}"
    if "table" in block_type:
        return _join_nonempty([_list_text(block.get("table_caption")), text, _list_text(block.get("table_footnote"))])
    if "image" in block_type or "chart" in block_type:
        return _join_nonempty([_list_text(block.get("image_caption")), text, _list_text(block.get("image_footnote"))])
    if "list" in block_type:
        return "\n".join(f"- {line}" for line in text.splitlines() if line.strip())
    if "code" in block_type:
        return f"```\n{text}\n```"
    return text


def _extract_block_text(block: dict[str, Any]) -> str:
    for key in (
        "text",
        "content",
        "table_body",
        "code_body",
        "list_items",
        "equation_body",
        "html",
        "latex",
    ):
        text = _extract_text(block.get(key))
        if text:
            return text

    lines = []
    for key in ("spans", "lines", "blocks"):
        text = _extract_text(block.get(key))
        if text:
            lines.append(text)
    return _join_nonempty(lines)


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _normalize_text(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return _join_nonempty(_extract_text(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "content", "html", "latex"):
            text = _extract_text(value.get(key))
            if text:
                return text
        return _join_nonempty(_extract_text(value.get(key)) for key in ("spans", "lines", "blocks"))
    return ""


def _list_text(value: Any) -> str:
    text = _extract_text(value)
    if not text:
        return ""
    return text


def _normalize_text(value: str) -> str:
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())


def _join_nonempty(values: Any) -> str:
    return "\n\n".join(str(value).strip() for value in values if str(value).strip())


def _metadata(path: Path, settings: Settings, page: int, mineru_source: str) -> dict[str, Any]:
    return {
        "source": path.name,
        "source_path": str(path),
        "file_type": "pdf",
        "page": page,
        "parser": "mineru",
        "mineru_model_version": settings.mineru_model_version,
        "mineru_result_source": mineru_source,
    }


def _find_first(root: Path, pattern: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(path for path in root.rglob(pattern) if path.is_file())
    return matches[0] if matches else None


def _cache_dir(path: Path, settings: Settings) -> Path:
    return settings.mineru_cache_path / f"{path.stem}_{_sha256(path)[:12]}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
