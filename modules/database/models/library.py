"""Library models: items, books, access grants."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Computed, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class LibraryItemModel(Base):
    __tablename__ = "library_items"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    author: Mapped[str] = mapped_column(Text, nullable=False, default="")
    book_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    item_type: Mapped[str] = mapped_column(String(50), nullable=False, default="book")
    genre: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="finished")
    created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    library_path: Mapped[str] = mapped_column(Text, nullable=False)
    cover_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    isbn: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="public")
    meta_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('simple', coalesce(book_title, '')), 'A') || "
            "setweight(to_tsvector('simple', coalesce(author, '')), 'B') || "
            "setweight(to_tsvector('simple', coalesce(genre, '')), 'C') || "
            "setweight(to_tsvector('simple', coalesce(language, '')), 'D')",
            persisted=True,
        ),
    )

    book: Mapped[Optional[BookModel]] = relationship(
        back_populates="library_item", uselist=False, cascade="all, delete-orphan"
    )
    grants: Mapped[list[LibraryItemGrantModel]] = relationship(
        back_populates="library_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_library_items_updated", "updated_at", postgresql_using="btree"),
        Index("idx_library_items_owner", "owner_id", postgresql_where="owner_id IS NOT NULL"),
        Index("idx_library_items_visibility", "visibility"),
        Index("idx_library_items_item_type", "item_type"),
        Index("idx_library_items_search", "search_vector", postgresql_using="gin"),
        Index("idx_library_items_meta", "meta_json", postgresql_using="gin"),
    )


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("library_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    genre: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cover_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    isbn: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    library_item: Mapped[LibraryItemModel] = relationship(back_populates="book")


class LibraryItemGrantModel(Base):
    __tablename__ = "library_item_grants"

    entry_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("library_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    subject_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    permission: Mapped[str] = mapped_column(String(20), primary_key=True)
    granted_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    granted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    library_item: Mapped[LibraryItemModel] = relationship(back_populates="grants")

    __table_args__ = (
        Index("idx_grants_entry", "entry_id"),
        Index("idx_grants_subject", "subject_type", "subject_id"),
    )
