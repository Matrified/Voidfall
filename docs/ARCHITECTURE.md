# VOIDFALL — Architecture

This document explains how VOIDFALL is put together and the reasoning behind the major
decisions. It is written for an engineer picking the project up for the first time.

## Guiding principle: engine authority

The single most important rule: **the engine owns all truth.** World state, combat,
inventory, movement, quests, persistence, and every game rule live in a pure Python
package (`domain`) that has no knowledge of HTTP, databases, or the AI. The Large Language
Model is confined to narration and can never mutate state or contradict the engine.

This gives us three things a typical "AI game" lacks:
1. **Determinism** — the same inputs always produce the same result.
2. **Testability** — the engine is exercised in complete isolation.
3. **Safety** — the AI cannot cheat, hallucinate loot, or break the world.

## Layered (clean) architecture

```
┌─────────────────────────────────────────────────────────────┐
│  app/        FastAPI: config, auth, db, cache, routes         │  interface / I/O
│  narration/  LLM providers, boundary, interpreter, ASCII art  │  adapters
│  parser/     free-form text → Engine_Action                   │  adapters
├─────────────────────────────────────────────────────────────┤
│  domain/     ECS, systems, events, RNG, quests, effects, save │  pure core (no I/O)
└─────────────────────────────────────────────────────────────┘
```

Dependencies point **inward**. `domain` imports nothing from `app`, `parser`, or
`narration`. You can import the engine into a script and play a whole game with zero
framework, database, or network — which is exactly what the property tests do.

## The Entity Component System

- **Entity**: an integer id.
- **Component**: a frozen-friendly dataclass holding one aspect of state (`Position`,
  `Health`, `Inventory`, `Item`, `Hidden`, ...). No behavior.
- **System**: a function operating over entities that possess a set of components
  (`movement`, `inventory`, `combat`).

The `World` stores components in `type -> {entity_id -> component}` maps and exposes a
small, deliberate API (`spawn`, `add`, `remove`, `query`, `get`). Queries return entity
ids sorted for deterministic iteration. Equality is by value, which is what makes the
determinism and round-trip tests possible.

## Determinism

`Rng` is a SplitMix64 generator whose entire state is `(seed, cursor)`. `cursor` is simply
the number of values drawn. Persisting the pair reproduces the exact stream position after
a save/load. Every stochastic system (combat, world tick) draws only from this source, so
two identical playthroughs are bit-for-bit identical — verified by a hypothesis property
test.

## The natural-language pipeline

1. **Parser** (`parser/`) tokenizes input, strips descriptive modifiers (kept for flavor),
   and tries to resolve a **canonical** action with concrete targets against the current
   room + inventory.
2. If it resolves cleanly → the **engine** applies it authoritatively.
3. If not → it becomes a **free-form** request handled by the **interpreter**
   (`narration/interpreter.py`).

The parser never calls the LLM. Ambiguous targets ask for clarification; unknown verbs and
unresolved targets flow to free-form interpretation rather than erroring.

## The AI boundary

`narration/`:
- **providers/** — a provider-agnostic `LLMProvider` protocol with OpenAI, Gemini, and
  Ollama adapters, plus a factory that reads configuration. Any failure raises
  `LLMUnavailable` so callers can fall back.
- **interpreter.py** — builds a **read-only** scene snapshot, asks the model for JSON
  `{ narration, effects, art }`, and coerces the result. Effects are *proposals only*.
- **domain/effects.py** — the authoritative whitelist. Each effect (`reveal`, `heal`,
  `hurt`, `reputation`, `journal`, `flag`) is validated and clamped before it touches the
  world. Unknown effect kinds are silently dropped.

Because the LLM only ever rephrases an already-resolved outcome or proposes bounded,
validated effects, it structurally cannot introduce facts that contradict the engine.

## Persistence

`domain/serialization.py` serializes the world to a versioned, JSON-friendly dict.
Components are tagged by a stable registry name (never a Python path), so refactoring
internal modules never breaks existing saves. A `SCHEMA_VERSION` is recorded and checked on
load, with a migration hook (`v1 → v2` already implemented). The interface layer stores
save payloads in PostgreSQL (prod) or SQLite (dev), scoped to the owning user.

## Caching

`app/cache.py` defines a `Cache` protocol with an in-process implementation (TTL) and a
Redis implementation, selected by configuration. Consumers depend only on the protocol.
Save listings use read-through caching with explicit invalidation on write.

## Attributes and stamina

Attributes are not decorative — they are read directly by the systems that use them:

- `domain/stats.py::effective_stats` folds Strength (attack) and Dexterity (defense) into
  combat stats on top of equipment bonuses.
- Attacking and forcing a locked passage both cost stamina (`domain/stats.py`); running out
  makes attacks land at a damage penalty, and forcing a door fails outright until you rest.
  Strength reduces the stamina cost of forcing something open.
- Resting (`Engine._rest`) restores health, mana, and stamina, scaled by Constitution.
- Charisma amplifies reputation swings in `domain/effects.py::_reputation`.

This keeps attributes mechanically load-bearing rather than flavor text on a stat sheet.

## Rendering: illustration → ASCII, not hand-typed art

`frontend/src/scenes/illustrations.ts` paints each scene as a real vector illustration at
a fixed internal resolution (silhouettes, radial-gradient glows, gradients for sky and
ground) using the 2D canvas API. `frontend/src/scenes/asciify.ts` then downsamples that
illustration to the target character-grid size and maps each resulting pixel's luminance
to a character from a density ramp, keeping the pixel's real sampled color. This is the
same technique behind image-to-ASCII converters, and it produces far higher detail and
color fidelity than authoring character grids by hand. NPC/creature portraits
(`scenes/portraits.ts`) use the same pipeline at a smaller size.

`SceneCanvas` renders the resulting character grid every frame and layers genuinely
rendered weather on top — rain as falling line segments, fog as drifting translucent
gradient bands — rather than describing weather in text. A torch light-cone effect (a
swaying radial gradient in "screen" blend mode) activates when a light-slot item is
equipped.

## Front end

A React + TypeScript app rendered inside a simulated CRT monitor:
- **SceneCanvas** — see above; the CRT shell adds scanlines, colored flicker, a screen
  shake and flash on taking damage, and a power-on boot sequence.
- **Compass** — a living SVG needle that idly drifts and eases toward an exit on hover,
  rather than a static character grid.
- **Backpack** — a slotted grid inventory with hover tooltips instead of a plain list.
- **SoundEngine** synthesizes everything from oscillators and filtered noise via the Web
  Audio API: looping ambience beds that cross-fade, and one-shot SFX keyed to story events.
  Settings persistence is versioned (`Settings.tsx`) so a change to a default value is
  never silently overridden by a stale save from an earlier build.
- The narration log parses ANSI to styled spans and types text out character by character.
- All motion respects `prefers-reduced-motion` and a manual reduced-motion toggle.

## Testing strategy

- **Unit** — RNG, ECS, parser, systems, effects, cache.
- **Integration** — the FastAPI app end-to-end via `TestClient` (auth, saves, ownership,
  admin).
- **Property-based** (hypothesis) — the two invariants that must never break: save
  round-trip and engine determinism.

Tests are hermetic: `conftest.py` forces `LLM_PROVIDER=none`, so the suite never touches a
live model, even if a developer has one configured in `.env`.
