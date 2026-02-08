"""Resume position model."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ResumePositionModel(Base):
    __tablename__ = "resume_positions"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="time")
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    base_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("idx_resume_updated", "user_id", "updated_at"),
    )
