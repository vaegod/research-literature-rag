from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.document_service import build_knowledge_base


def main() -> None:
    result = build_knowledge_base(force_rebuild=True)
    print(f"Loaded documents: {result.loaded_documents}")
    print(f"Generated chunks: {result.generated_chunks}")
    print(f"Vector store: {result.vector_store_path}")


if __name__ == "__main__":
    main()
