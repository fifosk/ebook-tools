"""Bookmark model."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class BookmarkModel(Base):
    __tablename__ = "bookmarks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    item_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="time")
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False, default="Bookmark")
    position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    base_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    segment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("idx_bookmarks_user_job", "user_id", "job_id"),
        Index("idx_bookmarks_created", "user_id", "job_id", "created_at"),
    )
