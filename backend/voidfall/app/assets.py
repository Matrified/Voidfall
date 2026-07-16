"""Scene asset generation and caching.

This is the "the world builds its own art library" pipeline. The first time a scene is
requested, concept art is generated once via an image model (OpenRouter), decoded, and
written to a content-addressed file on disk. Every subsequent request — this run or any
future run — is served straight from that cache. Art is never regenerated while it exists.

Generation is intentionally lazy and cached, so the ongoing cost is a handful of images
for the whole game, and the frontend fetches them in the background without blocking play.
"""

from __future__ import annotations

import base64
import binascii
import logging
import threading
from pathlib import Path

import httpx

from .config import Settings

logger = logging.getLogger("voidfall.assets")

# A shared visual language keeps every generated scene coherent on the CRT.
_STYLE = (
    "dark fantasy / retro sci-fi concept art, painterly, highly atmospheric, cinematic "
    "wide shot, moody volumetric lighting, muted teal-amber-crimson palette, deep shadows, "
    "no characters, no people, no text, no watermark, 16:9"
)

_SCENE_PROMPTS: dict[str, str] = {
    "gate": "the ruined stone gate of a dead castle at night in cold rain, a single "
            "guttering brazier, a torn banner, a broken cart half-sunk in mud",
    "hall": "a vast ruined great hall with a receding colonnade of broken pillars, a "
            "distant brazier glowing at the far end, dust in the air",
    "crypt": "a flooded stone crypt, carved tombstones half-submerged in still black "
             "water, faint green witchlight glow",
    "forest": "a black pine forest at night, thin cold mist between the trunks, a faint "
              "distant firelight deep in the woods",
    "vault": "a sealed treasure vault of a dead keep, gold glinting in torchlight, a "
             "stone bier at the center, ancient and untouched",
    "village": "an abandoned plague village square under thick grey fog at dusk, empty "
               "timber houses with open doors, a looming church steeple",
    "church": "the interior of a rotting gothic church at deep night, a great rose window "
              "glowing faint violet, shattered pews, columns in shadow",
    "clinic": "the interior of a ruined field clinic, overturned cots with dark "
              "bloodstains, a faded red medical cross, cold clinical light",
    "ship": "the docking bay of a derelict starship, red emergency lighting, scarred "
            "metal bulkheads, floating dust, dead consoles",
    "bridge": "the silent bridge of a derelict starship, a huge viewport showing a slow "
              "wrong-colored dying star, frozen consoles, cold blue glow",
    "shaft": "a cramped derelict starship maintenance shaft, exposed conduits and cabling, "
             "teal and red warning lights, deep claustrophobic shadow",
}


class AssetService:
    """Generates and caches scene concept art. Thread-safe per scene."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._dir = Path(settings.asset_cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    # -- public API --------------------------------------------------------

    def path_if_cached(self, scene_key: str) -> Path | None:
        path = self._path(scene_key)
        return path if path.exists() else None

    def get_or_create(self, scene_key: str) -> Path | None:
        """Return the cached art path, generating it once if needed.

        Returns ``None`` if generation is unavailable or fails, so the caller (and the
        frontend) can fall back to procedural rendering.
        """
        if scene_key not in _SCENE_PROMPTS:
            return None
        cached = self.path_if_cached(scene_key)
        if cached:
            return cached
        if not self._settings.image_generation_available:
            return None

        lock = self._lock_for(scene_key)
        with lock:
            # Re-check inside the lock: another request may have just generated it.
            cached = self.path_if_cached(scene_key)
            if cached:
                return cached
            return self._generate(scene_key)

    # -- internals ---------------------------------------------------------

    def _path(self, scene_key: str) -> Path:
        return self._dir / f"{scene_key}.png"

    def _lock_for(self, scene_key: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(scene_key, threading.Lock())

    def _generate(self, scene_key: str) -> Path | None:
        prompt = f"{_SCENE_PROMPTS[scene_key]}. {_STYLE}"
        try:
            png = self._request_image(prompt)
        except Exception as exc:  # noqa: BLE001 - any failure -> procedural fallback
            logger.warning("scene art generation failed for %s: %s", scene_key, exc)
            return None
        if png is None:
            return None
        path = self._path(scene_key)
        path.write_bytes(png)
        logger.info("generated and cached scene art: %s (%d bytes)", scene_key, len(png))
        return path

    def _request_image(self, prompt: str) -> bytes | None:
        s = self._settings
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {s.openrouter_api_key}"},
            json={
                "model": s.image_model,
                "messages": [{"role": "user", "content": prompt}],
                "modalities": ["image", "text"],
            },
            timeout=s.image_timeout_seconds,
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        images = message.get("images") or []
        if not images:
            return None
        url = images[0]["image_url"]["url"]
        if "," not in url:
            return None
        try:
            return base64.b64decode(url.split(",", 1)[1])
        except (binascii.Error, ValueError):
            return None
