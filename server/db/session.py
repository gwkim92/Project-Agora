from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.config import settings


def get_engine() -> Engine:
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    # SQLAlchemy 2.x style engine
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)


_SessionLocal: sessionmaker[Session] | None = None


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return _SessionLocal


def db_session() -> Iterator[Session]:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

