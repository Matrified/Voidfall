"""Local Ollama provider — free, private, offline."""

from __future__ import annotations

import httpx

from .base import LLMUnavailable


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, base_url: str, timeout: float) -> None:
        self._model = model or "llama3.1"
        self._base = (base_url or "http://localhost:11434").rstrip("/")
        self._timeout = timeout

    def generate(self, system: str, user: str, *, json_mode: bool = False) -> str:
        body: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.9},
        }
        if json_mode:
            body["format"] = "json"
        try:
            response = httpx.post(
                f"{self._base}/api/chat", json=body, timeout=self._timeout
            )
            response.raise_for_status()
            return response.json()["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMUnavailable(f"Ollama request failed: {exc}") from exc
