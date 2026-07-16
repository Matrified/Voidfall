<div align="center">

# ◄ VOIDFALL ►

### A Natural Language RPG Engine

Play a dark-fantasy RPG by typing plain English into a living, glitching CRT terminal.
There is no menu. A deterministic game engine is the sole authority over the world;
an AI is used only to narrate it.

[![CI](https://github.com/OWNER/voidfall/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/voidfall/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

```
> pry the barricade open using the crowbar
You work the crowbar into the gap. With a tortured groan of rusted metal and
splintering wood, the way east gives way.

> search the locked cabinet for records
In a locked cabinet you find the physician's antitoxin — the cure.
Quest complete: The Hollow Harvest.
```

Say what you want to do, in your own words, and the world responds.

## Why VOIDFALL is different

Most "AI text adventures" let a language model invent the world turn by turn, which means
it can also contradict itself, hand out items that don't exist, or forget a locked door is
locked. VOIDFALL splits authority instead:

```
 player input ─▶ Parser ─▶ Engine_Action ─▶  ENGINE (authoritative)  ─▶ Outcome + events
                                                        │
                          free-form text ─▶ Narrator (LLM) ─▶ proposes effects
                                                        │
                                        Engine validates & clamps every effect
                                                        │
                                                        ▼
                                            colored ASCII scene + narration + sound
```

- **Canonical actions** — move, take, equip, attack, unlock/force — resolve instantly
  inside the engine. No AI call, no latency, cannot be talked around.
- **Free-form actions** — "look in the crack", "pray at the altar", "search the cabinet" —
  are interpreted by an LLM, which may *propose* narrative effects from a fixed,
  server-validated whitelist (reveal a hidden object, nudge reputation, restore a little
  stamina). The engine clamps and applies them; the AI never gets to declare that a locked
  door opened or a fight was won.
- Play works with **no AI configured at all** — free-form actions fall back to an
  engine-authored response that still surfaces hand-placed discoveries.

## Choose your story

Three self-contained worlds, selectable from the title screen — each with its own rooms,
enemies, items, and quest line, built on the same engine:

| Story | Setting |
|---|---|
| **The Fall of Greyhelm** | A rain-drowned medieval keep, a lost heir, a debt owed to the dead |
| **The Hollow Harvest** | A fog-bound plague village where the dead won't stay down |
| **The Derelict Aurora** | A silent starship, a severed distress call, something aboard |

## Features

**World & rules**
- Entity Component System with deterministic, type-safe component queries
- A custom SplitMix64 RNG serialized as `(seed, cursor)` — perfectly reproducible runs
- Movement, inventory, equipment, and turn-based combat, all engine-owned
- Character attributes (Strength, Dexterity, Constitution, Intelligence, Wisdom,
  Charisma) with real mechanical effects: Strength adds damage and cuts the stamina cost
  of forcing doors, Dexterity adds defense, Constitution speeds recovery when resting,
  Charisma swings reputation checks
- A stamina economy — fighting and forcing doors costs stamina; run dry and you fight
  fatigued until you rest
- Quests that advance through **exploration**, not menus — discovering hidden lore sets
  the flags that complete them
- Save/load with schema versioning and migrations, verified by a round-trip property test

**Natural language**
- A parser resolves precise actions instantly and hands everything else to the narrator,
  including semantic movement ("proceed into the hall", "force the barricade")
- Any item marked as a tool (a key, a crowbar, a keycard) can unlock *or force* a barred
  passage — a real engine action with a stamina cost, not a line of flavor text
- Works with OpenAI, Google Gemini, or a local Ollama model — or no AI at all

**Presentation**
- Every scene is painted as a real vector illustration internally, then converted to a
  dense, full-color ASCII image — high detail, not hand-typed character art
- Live rendered weather: rain as falling streaks, fog as drifting translucent bands, a
  torch light-cone that sways when one is lit — not text describing weather, the weather
  itself
- NPCs and creatures get their own small ASCII portrait when you encounter them
- A slotted grid backpack and a living compass with a needle that idles and settles
  toward known exits
- A curved CRT monitor shell: scanlines, colored flicker, screen shake and a flash on
  taking damage, a boot-up power-on sequence
- A fully procedural sound engine (Web Audio, no audio files): looping ambience — rain,
  wind, a cavern drip — and reactive one-shot effects for hits, unlocking, discovery,
  footsteps, and more
- Keyboard-first: command history, autocomplete, and accessibility options
  (reduced motion, high contrast)

**Service**
- FastAPI backend with JWT authentication, per-user cloud saves, and an admin surface
- Redis-or-in-memory caching with read-through and invalidation
- Structured logging with correlation IDs and a global error boundary
- Auto-generated OpenAPI documentation

## Tech stack

| Layer | Technology |
|---|---|
| Engine | Python 3.11+, standard library, dataclasses |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, PyJWT, bcrypt |
| Data | PostgreSQL (production) · SQLite (development) · Redis (cache) |
| AI | OpenAI / Google Gemini / Ollama — pluggable, optional |
| Frontend | React 18, TypeScript 5, Vite, Canvas 2D, Web Audio, lucide-react |
| Tooling | pytest, hypothesis, ruff, mypy, ESLint, Docker, GitHub Actions |

## Getting started

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn voidfall.app.main:app --reload
```
API and interactive docs: <http://localhost:8000/docs>

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open the URL Vite prints (typically <http://localhost:5173>).

### Docker (full stack)
```bash
docker compose up --build
```

## Enabling AI narration (optional)

The game is complete without it. To turn on rich, model-written narration for free-form
actions, copy `backend/.env.example` to `backend/.env` and set a provider. Google Gemini
has a usable free tier:

```env
VOIDFALL_LLM_PROVIDER=gemini
VOIDFALL_LLM_MODEL=gemini-flash-lite-latest
VOIDFALL_LLM_API_KEY=your-key-here
```

Get a key at <https://aistudio.google.com/apikey>. OpenAI (`gpt-4o-mini`) and a local
Ollama model work the same way — see `.env.example` for details. `.env` is gitignored.

## Testing

```bash
cd backend
pytest                       # unit, integration, and property-based tests
ruff check voidfall tests
mypy voidfall/domain

cd ../frontend
npm run typecheck
npm run build
```

Two properties are enforced directly, across every scenario:
- **Round-trip** — `deserialize(serialize(world)) == world` for any world
- **Determinism** — the same action on equal worlds with the same seed/cursor produces
  an identical result

## How to play

There is no command list to memorize. A few things that always work:

| You might type | What happens |
|---|---|
| `go north` / `north` | Moves you, if that way is open |
| `proceed into the hall` | Semantic movement — matched by destination, not just compass words |
| `search the broken cart` | A discovery check — may reveal something hand-placed |
| `equip the longsword` | Changes your effective combat stats |
| `force the door using the crowbar` | Opens a barred passage if you're carrying a tool, at a stamina cost |
| `attack the ghoul` | Deterministic, rule-based combat |
| `rest` | Recovers health, mana, and stamina, faster with higher Constitution |
| `talk to the gatekeeper` | Free-form conversation, with a portrait shown for who you're facing |

## Project layout

```
voidfall/
├─ backend/
│  └─ voidfall/
│     ├─ domain/        the pure engine — ECS, systems, events, RNG, quests, effects, save
│     ├─ parser/        natural language → structured Engine_Action
│     ├─ narration/     LLM providers, the narration boundary, ASCII art hooks
│     ├─ content/       hand-authored worlds and selectable scenarios
│     └─ app/           FastAPI — config, auth, database, cache, routes, game service
├─ frontend/
│  └─ src/
│     ├─ components/    panels, the scene canvas, backpack, compass, portraits, modals
│     ├─ scenes/        vector illustrations, the image-to-ASCII pipeline, NPC faces
│     ├─ audio/         the procedural sound engine
│     └─ lib/           ANSI parsing, icon mapping
├─ docs/                architecture notes
└─ docker-compose.yml
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a deeper look at how it fits
together.

## License

MIT — see [LICENSE](LICENSE).
