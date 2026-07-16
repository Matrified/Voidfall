"""Application configuration, loaded from the environment.

Configuration is externalized (12-factor style). In development the defaults let the
service run with zero setup on SQLite. In production the secret key must be supplied or
startup fails — we never ship a real deployment with a known signing key.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOIDFALL_", env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./voidfall.db"

    # Optional Redis cache. When empty, an in-process cache is used.
    redis_url: str = ""

    # --- LLM narration ---------------------------------------------------
    # provider: "none" | "openai" | "gemini" | "ollama"
    llm_provider: str = "none"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""      # override for OpenAI-compatible / Ollama endpoints
    llm_timeout_seconds: float = 12.0
    llm_ascii_art: bool = True  # allow the model to draw scene art

    # --- Scene image generation (OpenRouter) -----------------------------
    # When a key is set, scene concept art is generated once, cached to disk forever, and
    # served to the client for half-block terminal rendering. When absent, the client
    # falls back to its built-in procedural painter.
    openrouter_api_key: str = ""
    image_model: str = "google/gemini-2.5-flash-image"
    image_gen_enabled: bool = True
    image_timeout_seconds: float = 60.0
    asset_cache_dir: str = "asset_cache"

    @property
    def image_generation_available(self) -> bool:
        return self.image_gen_enabled and bool(self.openrouter_api_key)

    # Auth
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 3600

    # CORS — the Vite dev server by default.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Content
    default_seed: int = 1337

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.jwt_secret == "dev-only-insecure-secret-change-me":
        raise RuntimeError("VOIDFALL_JWT_SECRET must be set in production")
    return settings
