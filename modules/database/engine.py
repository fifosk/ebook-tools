"""SQLAlchemy engine singleton and session helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV = "DATABASE_URL"
_DEFAULT_URL = "postgresql+psycopg2://ebook_tools:ebook_tools_dev@localhost:5432/ebook_tools"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_database_url() -> str:
    return os.environ.get(DATABASE_URL_ENV, _DEFAULT_URL)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """Dispose the global engine and clear the factory."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
