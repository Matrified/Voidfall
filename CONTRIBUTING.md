# Contributing to VOIDFALL

Thanks for your interest. This project values clean, tested, readable code over cleverness.

## Ground rules

1. **The engine is authoritative.** Game logic lives in `backend/voidfall/domain` and must
   have no dependency on the web framework, the database, or the LLM. If you find yourself
   importing `app`, `parser`, or `narration` from `domain`, stop and rethink.
2. **The AI never decides outcomes.** New AI-driven behavior must go through the sanctioned
   effect whitelist in `domain/effects.py`, validated and clamped by the engine.
3. **Determinism is sacred.** Any randomness must draw from `world.rng`. Never use Python's
   global `random` or `datetime.now()` inside the engine.

## Development setup

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\Activate.ps1   # or: source .venv/bin/activate
pip install -e ".[dev]"

# Front end
cd ../frontend
npm install
```

## Before you open a PR

Run the full gate locally — CI runs the same checks:

```bash
# Backend
cd backend
ruff check voidfall tests
mypy voidfall/domain
pytest

# Front end
cd ../frontend
npm run typecheck
npm run build
```

## Adding to the game

- **A new component**: add the dataclass to `domain/components.py` and register it in
  `COMPONENT_REGISTRY` (this is what makes it serializable).
- **A new system**: add a module under `domain/systems/` and dispatch to it from
  `domain/engine.py`. Publish events on the bus rather than reaching into other systems.
- **A new sanctioned effect**: extend `domain/effects.py` with validation and clamping, and
  document it in the interpreter's system prompt.
- **New content**: extend `content/world_seed.py`. Use `Hidden` with `set_flag` to let
  discoveries advance quests.
- **A new LLM provider**: implement the `LLMProvider` protocol in
  `narration/providers/` and wire it into the factory.

## Style

- Python: type-hinted, `ruff`-clean, `mypy --strict` on the domain. Prefer small, pure
  functions and clear names over comments that restate the code.
- TypeScript: strict mode, no `any` unless justified, components small and focused.
- Write a test for every bug fix and every new rule.
