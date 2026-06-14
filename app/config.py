from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")


def _path_from_env(name: str, default: str) -> Path:
    value = os.getenv(name, default)
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _int_from_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_from_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _list_from_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_version: str
    openai_compatible_api_key: str
    openai_compatible_base_url: str
    chat_model: str
    embedding_model: str
    cors_allow_origins: list[str]
    cors_allow_credentials: bool
    raw_docs_path: Path
    processed_docs_path: Path
    vector_store_path: Path
    experiment_records_path: Path
    eval_questions_path: Path
    eval_result_path: Path
    default_top_k: int
    chunk_size: int
    chunk_overlap: int
    chat_temperature: float
    max_upload_size_mb: int
    agent_router_mode: str
    retrieval_mode: str
    hybrid_dense_weight: float
    hybrid_bm25_weight: float
    hybrid_rrf_k: int
    retrieval_fetch_multiplier: int
    retrieval_min_candidates: int
    enable_reranker: bool
    reranker_model: str
    reranker_candidate_limit: int
    reranker_max_chars: int
    reranker_timeout_seconds: float
    trust_local_faiss_index: bool

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_compatible_api_key.strip())

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        openai_compatible_api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY", ""),
        openai_compatible_base_url=os.getenv(
            "OPENAI_COMPATIBLE_BASE_URL", "https://api.siliconflow.cn/v1"
        ),
        chat_model=os.getenv("CHAT_MODEL", "deepseek-ai/DeepSeek-V3"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
        cors_allow_origins=_list_from_env(
            "CORS_ALLOW_ORIGINS", "http://127.0.0.1:8010,http://localhost:8010"
        ),
        cors_allow_credentials=_bool_from_env("CORS_ALLOW_CREDENTIALS", False),
        raw_docs_path=_path_from_env("RAW_DOCS_PATH", "data/raw_docs"),
        processed_docs_path=_path_from_env("PROCESSED_DOCS_PATH", "data/processed_docs"),
        vector_store_path=_path_from_env("VECTOR_STORE_PATH", "vector_store/faiss_index"),
        experiment_records_path=_path_from_env(
            "EXPERIMENT_RECORDS_PATH", "data/experiments/experiment_records.json"
        ),
        eval_questions_path=_path_from_env("EVAL_QUESTIONS_PATH", "data/eval/rag_eval_questions.csv"),
        eval_result_path=_path_from_env("EVAL_RESULT_PATH", "data/eval/eval_result.csv"),
        default_top_k=_int_from_env("DEFAULT_TOP_K", 4),
        chunk_size=_int_from_env("CHUNK_SIZE", 800),
        chunk_overlap=_int_from_env("CHUNK_OVERLAP", 120),
        chat_temperature=_float_from_env("CHAT_TEMPERATURE", 0.2),
        max_upload_size_mb=_int_from_env("MAX_UPLOAD_SIZE_MB", 20),
        agent_router_mode=os.getenv("AGENT_ROUTER_MODE", "rule").strip().lower() or "rule",
        retrieval_mode=os.getenv("RETRIEVAL_MODE", "hybrid").strip().lower() or "hybrid",
        hybrid_dense_weight=_float_from_env("HYBRID_DENSE_WEIGHT", 0.65),
        hybrid_bm25_weight=_float_from_env("HYBRID_BM25_WEIGHT", 0.35),
        hybrid_rrf_k=_int_from_env("HYBRID_RRF_K", 60),
        retrieval_fetch_multiplier=_int_from_env("RETRIEVAL_FETCH_MULTIPLIER", 12),
        retrieval_min_candidates=_int_from_env("RETRIEVAL_MIN_CANDIDATES", 60),
        enable_reranker=_bool_from_env("ENABLE_RERANKER", False),
        reranker_model=os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3").strip(),
        reranker_candidate_limit=_int_from_env("RERANKER_CANDIDATE_LIMIT", 24),
        reranker_max_chars=_int_from_env("RERANKER_MAX_CHARS", 1800),
        reranker_timeout_seconds=_float_from_env("RERANKER_TIMEOUT_SECONDS", 30.0),
        trust_local_faiss_index=_bool_from_env("TRUST_LOCAL_FAISS_INDEX", True),
    )


def ensure_data_directories(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    for path in (
        settings.raw_docs_path,
        settings.processed_docs_path,
        settings.vector_store_path,
        settings.experiment_records_path.parent,
        settings.eval_questions_path.parent,
        settings.eval_result_path.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
