"""OpenAI (and OpenAI-compatible) chat-completions provider."""

from __future__ import annotations

import httpx

from .base import LLMUnavailable


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float) -> None:
        self._key = api_key
        self._model = model or "gpt-4o-mini"
        self._base = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout

    def generate(self, system: str, user: str, *, json_mode: bool = False) -> str:
        if not self._key:
            raise LLMUnavailable("missing OpenAI API key")
        body: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.9,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            response = httpx.post(
                f"{self._base}/chat/completions",
                headers={"Authorization": f"Bearer {self._key}"},
                json=body,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable(f"OpenAI request failed: {exc}") from exc
