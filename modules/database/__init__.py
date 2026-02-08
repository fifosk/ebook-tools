"""SQLAlchemy database layer for ebook-tools.

Provides the shared engine, session factory, and declarative base
used by all PostgreSQL-backed repositories.
"""

from .base import Base
from .engine import dispose_engine, get_db_session, get_engine

__all__ = ["Base", "get_engine", "get_db_session", "dispose_engine"]
