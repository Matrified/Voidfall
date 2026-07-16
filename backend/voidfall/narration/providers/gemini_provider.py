"""Google Gemini (Generative Language API) provider."""

from __future__ import annotations

import httpx

from .base import LLMUnavailable


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float) -> None:
        self._key = api_key
        self._model = model or "gemini-flash-lite-latest"
        self._base = (
            base_url or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        self._timeout = timeout

    def generate(self, system: str, user: str, *, json_mode: bool = False) -> str:
        if not self._key:
            raise LLMUnavailable("missing Gemini API key")
        # thinkingBudget=0 keeps latency low on 2.x "flash" models (harmless elsewhere).
        generation_config: dict = {
            "temperature": 0.9,
            "thinkingConfig": {"thinkingBudget": 0},
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": generation_config,
        }
        try:
            response = httpx.post(
                f"{self._base}/models/{self._model}:generateContent",
                params={"key": self._key},
                json=body,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable(f"Gemini request failed: {exc}") from exc
