"""HTTP routes.

Grouped into four routers: authentication, gameplay, cloud saves, and administration.
Each keeps its concern isolated; the game pipeline itself lives in ``game_service``.
"""

from __future__ import annotations

import json
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.serialization import SaveError, deserialize, serialize
from .assets import AssetService
from .auth import (
    create_access_token,
    current_user,
    hash_password,
    password_policy_error,
    require_admin,
    verify_password,
)
from .cache import get_cache
from .config import Settings, get_settings
from .db import SaveGame, User, get_db
from .game_service import game_service
from .schemas import (
    AdminUserView,
    CommandRequest,
    GameView,
    NewGameRequest,
    RegisterRequest,
    SaveRequest,
    SaveSummary,
    TokenResponse,
    UserResponse,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
game_router = APIRouter(prefix="/game", tags=["game"])
save_router = APIRouter(prefix="/saves", tags=["saves"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
asset_router = APIRouter(prefix="/assets", tags=["assets"])


@lru_cache
def _asset_service() -> AssetService:
    return AssetService(get_settings())


# --- scene assets ---------------------------------------------------------


@asset_router.get("/scene/{scene_key}")
async def scene_asset(scene_key: str) -> FileResponse:
    """Serve cached scene concept art, generating it once on first request.

    Generation runs in a threadpool so a slow image call never blocks the event loop; the
    frontend requests this in the background and shows a procedural scene meanwhile.
    """
    service = _asset_service()
    path = await run_in_threadpool(service.get_or_create, scene_key)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No art available for this scene")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},
    )


# --- auth -----------------------------------------------------------------


@auth_router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> User:
    policy_error = password_policy_error(body.password)
    if policy_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, policy_error)

    exists = db.scalar(select(User).where(User.username == body.username))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    # The very first account becomes the administrator.
    is_first = db.scalar(select(func.count()).select_from(User)) == 0
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        is_admin=is_first,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@auth_router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == form.username))
    # Same error whether the user is missing or the password is wrong.
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.id, settings))


@auth_router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> User:
    return user


# --- gameplay -------------------------------------------------------------
# Play is available to guests; only cloud saves require an account.


@game_router.post("/new", response_model=GameView)
def new_game(
    body: NewGameRequest, settings: Settings = Depends(get_settings)
) -> GameView:
    seed = body.seed if body.seed is not None else settings.default_seed
    return game_service.new_game(
        theme=body.theme, seed=seed, owner_id=None, player_name=body.player_name
    )


@game_router.post("/command", response_model=GameView)
def command(body: CommandRequest) -> GameView:
    view = game_service.command(body.session_id, body.text, owner_id=None)
    if view is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown session")
    return view


# --- cloud saves ----------------------------------------------------------


@save_router.post("", response_model=SaveSummary, status_code=201)
def create_save(
    body: SaveRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> SaveSummary:
    world = game_service.get_world(body.session_id, owner_id=None)
    if world is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown session")

    payload = json.dumps(serialize(world))
    save = SaveGame(owner_id=user.id, name=body.name, payload=payload)
    db.add(save)
    db.commit()
    db.refresh(save)
    get_cache().invalidate(f"saves:{user.id}")  # stored set changed
    return SaveSummary(
        id=save.id, name=save.name, turn=world.turn, updated_at=save.updated_at.isoformat()
    )


@save_router.get("", response_model=list[SaveSummary])
def list_saves(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[SaveSummary]:
    cache = get_cache()
    cache_key = f"saves:{user.id}"

    # Read-through cache: serve the cached list when present (R17.4).
    cached = cache.get(cache_key)
    if cached is not None:
        return [SaveSummary(**row) for row in json.loads(cached)]

    rows = db.scalars(select(SaveGame).where(SaveGame.owner_id == user.id)).all()
    summaries: list[SaveSummary] = []
    for row in rows:
        turn = json.loads(row.payload).get("turn", 0)
        summaries.append(
            SaveSummary(id=row.id, name=row.name, turn=turn, updated_at=row.updated_at.isoformat())
        )
    cache.set(cache_key, json.dumps([s.model_dump() for s in summaries]))
    return summaries


@save_router.post("/{save_id}/load", response_model=GameView)
def load_save(
    save_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> GameView:
    save = db.get(SaveGame, save_id)
    if save is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Save not found")
    if save.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your save")
    try:
        world = deserialize(json.loads(save.payload))
    except SaveError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return game_service.load_world(world, owner_id=None)


@save_router.delete("/{save_id}", status_code=204)
def delete_save(
    save_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    save = db.get(SaveGame, save_id)
    if save is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Save not found")
    if save.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your save")
    db.delete(save)
    db.commit()
    get_cache().invalidate(f"saves:{user.id}")  # stored set changed


# --- admin ----------------------------------------------------------------


@admin_router.get("/users", response_model=list[AdminUserView])
def admin_users(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[AdminUserView]:
    users = db.scalars(select(User)).all()
    return [
        AdminUserView(
            id=u.id,
            username=u.username,
            is_admin=u.is_admin,
            is_active=u.is_active,
            save_count=len(u.saves),
        )
        for u in users
    ]


@admin_router.post("/users/{user_id}/disable", response_model=AdminUserView)
def admin_disable_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserView:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    target.is_active = False
    db.commit()
    db.refresh(target)
    return AdminUserView(
        id=target.id,
        username=target.username,
        is_admin=target.is_admin,
        is_active=target.is_active,
        save_count=len(target.saves),
    )
