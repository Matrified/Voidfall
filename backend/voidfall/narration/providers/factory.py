"""Selects and constructs an LLM provider from settings.

Also honors the conventional environment variables (``OPENAI_API_KEY``,
``GOOGLE_API_KEY``) so a player can just export the standard key without learning our
prefixed names. Returns ``None`` when no provider is configured, in which case the game
runs fully on engine narration.
"""

from __future__ import annotations

import os

from ...app.config import get_settings
from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


def build_provider() -> LLMProvider | None:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    timeout = settings.llm_timeout_seconds

    if provider in ("", "none"):
        return None

    if provider == "openai":
        key = settings.llm_api_key or os.getenv("OPENAI_API_KEY", "")
        return OpenAIProvider(key, settings.llm_model, settings.llm_base_url, timeout)

    if provider == "gemini":
        key = settings.llm_api_key or os.getenv("GOOGLE_API_KEY", "")
        return GeminiProvider(key, settings.llm_model, settings.llm_base_url, timeout)

    if provider == "ollama":
        return OllamaProvider(settings.llm_model, settings.llm_base_url, timeout)

    return None
