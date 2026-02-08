"""Media analytics — generation stats and playback sessions.

Revision ID: 002
Revises: 001
Create Date: 2026-02-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 15. Media Generation Stats ───────────────────────────────
    op.create_table(
        "media_generation_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("track_kind", sa.String(20), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0"),
        sa.Column("sentence_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("job_id", "language", "track_kind", name="uq_gen_stats_job_lang_track"),
    )
    op.create_index("idx_gen_stats_language", "media_generation_stats", ["language"])
    op.create_index("idx_gen_stats_job_type", "media_generation_stats", ["job_type"])
    op.create_index("idx_gen_stats_created", "media_generation_stats", [sa.text("created_at DESC")])

    # ── 16. Playback Sessions ────────────────────────────────────
    op.create_table(
        "playback_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("track_kind", sa.String(20), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_playback_user_job", "playback_sessions", ["user_id", "job_id"])
    op.create_index("idx_playback_language", "playback_sessions", ["language"])
    op.create_index("idx_playback_started", "playback_sessions", [sa.text("started_at DESC")])


def downgrade() -> None:
    op.drop_table("playback_sessions")
    op.drop_table("media_generation_stats")
