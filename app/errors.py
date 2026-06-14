from __future__ import annotations


class DependencyMissingError(RuntimeError):
    """Raised when an optional runtime dependency is not installed."""


class ModelProviderError(RuntimeError):
    """Raised when an OpenAI-compatible model provider request fails."""

