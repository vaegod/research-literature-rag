from __future__ import annotations

from collections.abc import Iterator

from app.config import get_settings
from app.errors import DependencyMissingError, ModelProviderError


def _make_client(settings):
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency is installed in normal runs.
        raise DependencyMissingError("The `openai` package is required for chat completion.") from exc

    return OpenAI(
        api_key=settings.openai_compatible_api_key,
        base_url=settings.openai_compatible_base_url,
    )


def complete_chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
) -> str:
    settings = get_settings()
    if not settings.has_api_key:
        raise RuntimeError("OPENAI_COMPATIBLE_API_KEY is required for chat completion.")

    client = _make_client(settings)
    try:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.chat_temperature if temperature is None else temperature,
            stream=False,
        )
    except Exception as exc:  # pragma: no cover - depends on external provider behavior.
        raise ModelProviderError(f"Chat model request failed: {exc}") from exc
    return response.choices[0].message.content or ""


def stream_chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float | None = None,
) -> Iterator[str]:
    settings = get_settings()
    if not settings.has_api_key:
        raise RuntimeError("OPENAI_COMPATIBLE_API_KEY is required for chat completion.")

    client = _make_client(settings)
    try:
        stream = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.chat_temperature if temperature is None else temperature,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:  # pragma: no cover - depends on external provider behavior.
        raise ModelProviderError(f"Chat model streaming failed: {exc}") from exc
