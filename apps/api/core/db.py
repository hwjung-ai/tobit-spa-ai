from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.postgres_dsn,
    echo=settings.log_level.lower() == "debug",
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=Session
)


def init_db() -> None:
    # Import all models to register them with SQLModel
    # This is required for init_db() to create all tables
    import app.modules.inspector.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    with get_session_context() as session:
        yield session
