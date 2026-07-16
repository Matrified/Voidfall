"""Pydantic request/response models — the API's public contract."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool


class NewGameRequest(BaseModel):
    seed: int | None = None
    theme: str = "medieval"  # medieval | undead | starship
    player_name: str | None = None


class CommandRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=500)


# --- rich view sub-models -------------------------------------------------


class AttributeView(BaseModel):
    name: str
    value: int
    modifier: int


class PlayerView(BaseModel):
    name: str
    level: int
    exp: int
    exp_next: int
    attribute_points: int
    hp: int
    hp_max: int
    mp: int
    mp_max: int
    stamina: int
    stamina_max: int
    attributes: list[AttributeView]


class ItemView(BaseModel):
    name: str
    icon: str
    rarity: str
    quantity: int
    equipped: bool = False


class EntityView(BaseModel):
    glyph: str
    name: str
    note: str = ""


class QuestObjectiveView(BaseModel):
    text: str
    done: bool


class QuestView(BaseModel):
    name: str
    completed: bool
    objectives: list[QuestObjectiveView]


class ExitView(BaseModel):
    direction: str
    to: str  # destination name if discovered, else "unknown"
    locked: bool = False


class GameView(BaseModel):
    """Everything the terminal renders after a turn."""

    session_id: str
    echo: str = ""
    narration: str
    art: str | None = None
    scene: str = "gate"          # scene key the UI uses to pick/tint art

    location: str
    time: str
    weather: str
    exits: list[ExitView]        # for the compass/map panel

    ambience: str = "wind"       # looping ambient bed the UI should play
    sounds: list[str] = []       # one-shot sound cues for this turn

    player: PlayerView
    inventory: list[ItemView]
    equipped: list[ItemView]
    entities: list[EntityView]
    quests: list[QuestView]
    journal: list[str]

    turn: int
    success: bool
    code: str


class SaveRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1, max_length=120)


class SaveSummary(BaseModel):
    id: int
    name: str
    turn: int
    updated_at: str


class AdminUserView(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool
    save_count: int
