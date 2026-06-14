from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property

from app.config import Settings, get_settings
from app.errors import DependencyMissingError, ModelProviderError
from app.retriever.loaders import Document

try:
    from langchain_core.embeddings import Embeddings
except Exception:  # pragma: no cover - used only when LangChain is unavailable.

    class Embeddings:  # type: ignore[no-redef]
        pass


class OpenAICompatibleEmbeddings(Embeddings):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        batch_size: int = 32,
    ) -> None:
        if not api_key:
            raise RuntimeError("OPENAI_COMPATIBLE_API_KEY is required for embeddings.")
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.batch_size = batch_size

    @cached_property
    def client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in _batched(texts, self.batch_size):
            try:
                response = self.client.embeddings.create(model=self.model, input=batch)
            except Exception as exc:  # pragma: no cover - depends on external provider behavior.
                raise ModelProviderError(f"Embedding model request failed: {exc}") from exc
            vectors.extend([item.embedding for item in response.data])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def _batched(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def make_embeddings(settings: Settings | None = None) -> OpenAICompatibleEmbeddings:
    settings = settings or get_settings()
    return OpenAICompatibleEmbeddings(
        api_key=settings.openai_compatible_api_key,
        base_url=settings.openai_compatible_base_url,
        model=settings.embedding_model,
    )


def build_vector_store(chunks: list[Document], settings: Settings | None = None) -> None:
    if not chunks:
        raise ValueError("No document chunks to index.")

    try:
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:  # pragma: no cover - dependency is installed in normal runs.
        raise DependencyMissingError("The `langchain-community` package is required for FAISS.") from exc

    settings = settings or get_settings()
    settings.vector_store_path.mkdir(parents=True, exist_ok=True)
    store = FAISS.from_documents(chunks, make_embeddings(settings))
    store.save_local(str(settings.vector_store_path))


def load_vector_store(settings: Settings | None = None):
    try:
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:  # pragma: no cover - dependency is installed in normal runs.
        raise DependencyMissingError("The `langchain-community` package is required for FAISS.") from exc

    settings = settings or get_settings()
    index_file = settings.vector_store_path / "index.faiss"
    if not index_file.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {settings.vector_store_path}. "
            "Run `python scripts/build_index.py` or call `/knowledge/build` first."
        )
    if not settings.trust_local_faiss_index:
        raise RuntimeError(
            "FAISS metadata loading is disabled. Set TRUST_LOCAL_FAISS_INDEX=true only "
            "when the index was generated locally by this project."
        )
    return FAISS.load_local(
        str(settings.vector_store_path),
        make_embeddings(settings),
        # LangChain stores FAISS document metadata through pickle. The project only loads
        # indexes from VECTOR_STORE_PATH and documents this as a local-trust boundary.
        allow_dangerous_deserialization=settings.trust_local_faiss_index,
    )


def similarity_search(
    query: str,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[tuple[Document, float]]:
    settings = settings or get_settings()
    top_k = top_k or settings.default_top_k
    store = load_vector_store(settings)
    return store.similarity_search_with_score(query, k=top_k)
