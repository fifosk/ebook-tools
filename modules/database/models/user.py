"""User and session models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin


class UserModel(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    roles: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    sessions: Mapped[list[SessionModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)

    user: Mapped[UserModel] = relationship(back_populates="sessions")
