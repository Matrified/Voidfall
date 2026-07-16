"""Database setup and ORM models.

SQLAlchemy 2.0 style. SQLite in development, PostgreSQL in production — the only
difference is the connection URL. Two tables: users and save games. Save payloads are
stored as JSON text so they remain engine-version friendly via the schema migrations in
``domain.serialization``.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import ForeignKey, String, Text, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from .config import get_settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(default=lambda: dt.datetime.now(dt.UTC))

    saves: Mapped[list[SaveGame]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class SaveGame(Base):
    __tablename__ = "save_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    payload: Mapped[str] = mapped_column(Text)  # JSON-serialized world
    created_at: Mapped[dt.datetime] = mapped_column(default=lambda: dt.datetime.now(dt.UTC))
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )

    owner: Mapped[User] = relationship(back_populates="saves")


_settings = get_settings()
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they do not yet exist."""
    Base.metadata.create_all(engine)


def get_db():
    """FastAPI dependency yielding a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
