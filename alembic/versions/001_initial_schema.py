"""Initial schema — all 14 tables.

Revision ID: 001
Revises:
Create Date: 2026-02-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("roles", JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_users_username", "users", ["username"])

    # ── 2. Sessions ───────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("ip_address", INET, nullable=True),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index(
        "idx_sessions_expires", "sessions", ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # ── 3. Library Items ──────────────────────────────────────────
    op.create_table(
        "library_items",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("author", sa.Text, nullable=False, server_default=""),
        sa.Column("book_title", sa.Text, nullable=False, server_default=""),
        sa.Column("item_type", sa.String(50), nullable=False, server_default="book"),
        sa.Column("genre", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default=""),
        sa.Column("status", sa.String(50), nullable=False, server_default="finished"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("library_path", sa.Text, nullable=False),
        sa.Column("cover_path", sa.Text, nullable=True),
        sa.Column("isbn", sa.String(30), nullable=True),
        sa.Column("source_path", sa.Text, nullable=True),
        sa.Column("owner_id", sa.String(255), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="public"),
        sa.Column("meta_json", JSONB, nullable=False, server_default="{}"),
    )

    # Add the generated tsvector column
    op.execute("""
        ALTER TABLE library_items ADD COLUMN search_vector TSVECTOR
        GENERATED ALWAYS AS (
            setweight(to_tsvector('simple', coalesce(book_title, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(author, '')), 'B') ||
            setweight(to_tsvector('simple', coalesce(genre, '')), 'C') ||
            setweight(to_tsvector('simple', coalesce(language, '')), 'D')
        ) STORED
    """)

    op.create_index("idx_library_items_updated", "library_items", [sa.text("updated_at DESC")])
    op.create_index(
        "idx_library_items_owner", "library_items", ["owner_id"],
        postgresql_where=sa.text("owner_id IS NOT NULL"),
    )
    op.create_index("idx_library_items_visibility", "library_items", ["visibility"])
    op.create_index("idx_library_items_item_type", "library_items", ["item_type"])
    op.create_index("idx_library_items_search", "library_items", ["search_vector"], postgresql_using="gin")
    op.create_index("idx_library_items_meta", "library_items", ["meta_json"], postgresql_using="gin")

    # ── 4. Books ──────────────────────────────────────────────────
    op.create_table(
        "books",
        sa.Column("id", sa.String(255), sa.ForeignKey("library_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("author", sa.Text, nullable=True),
        sa.Column("genre", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("cover_path", sa.Text, nullable=True),
        sa.Column("isbn", sa.String(30), nullable=True),
        sa.Column("source_path", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 5. Library Item Grants ────────────────────────────────────
    op.create_table(
        "library_item_grants",
        sa.Column("entry_id", sa.String(255), sa.ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("permission", sa.String(20), nullable=False),
        sa.Column("granted_by", sa.String(255), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("entry_id", "subject_type", "subject_id", "permission"),
    )
    op.create_index("idx_grants_entry", "library_item_grants", ["entry_id"])
    op.create_index("idx_grants_subject", "library_item_grants", ["subject_type", "subject_id"])

    # ── 6. Config Snapshots ───────────────────────────────────────
    op.create_table(
        "config_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("snapshot_id", sa.String(50), unique=True, nullable=False),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config_json", JSONB, nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
    )
    op.create_index(
        "idx_config_snap_active", "config_snapshots", ["is_active"],
        postgresql_where=sa.text("is_active = TRUE"),
    )
    op.create_index("idx_config_snap_created", "config_snapshots", [sa.text("created_at DESC")])
    op.create_index("idx_config_snap_source", "config_snapshots", ["source"])

    # ── 7. Config Audit Log ───────────────────────────────────────
    op.create_table(
        "config_audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("snapshot_id", sa.String(50), nullable=True),
        sa.Column("group_name", sa.String(100), nullable=True),
        sa.Column("key_name", sa.String(255), nullable=True),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("idx_audit_timestamp", "config_audit_log", [sa.text("timestamp DESC")])
    op.create_index("idx_audit_username", "config_audit_log", ["username"])
    op.create_index("idx_audit_action", "config_audit_log", ["action"])
    op.create_index("idx_audit_group", "config_audit_log", ["group_name"])

    # ── 8. Config Sensitive Keys ──────────────────────────────────
    op.create_table(
        "config_sensitive_keys",
        sa.Column("key_path", sa.String(255), primary_key=True),
        sa.Column("mask_in_ui", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("mask_in_export", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("mask_in_audit", sa.Boolean, server_default=sa.text("TRUE")),
    )
    # Seed default sensitive keys
    op.execute("""
        INSERT INTO config_sensitive_keys (key_path) VALUES
            ('ollama_api_key'), ('database_url'), ('job_store_url'),
            ('api_keys.ollama'), ('api_keys.openai'), ('api_keys.anthropic')
        ON CONFLICT DO NOTHING
    """)

    # ── 9. Config Secrets ─────────────────────────────────────────
    op.create_table(
        "config_secrets",
        sa.Column("key_path", sa.String(255), primary_key=True),
        sa.Column("encrypted_value", sa.LargeBinary, nullable=False),
        sa.Column("encryption_version", sa.Integer, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=True),
    )

    # ── 10. Config Group Settings ─────────────────────────────────
    op.create_table(
        "config_group_settings",
        sa.Column("group_name", sa.String(100), primary_key=True),
        sa.Column("is_collapsed", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("display_order", sa.Integer, server_default="0"),
        sa.Column("custom_icon", sa.String(100), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
    )
    # Seed default groups
    op.execute("""
        INSERT INTO config_group_settings (group_name, display_order) VALUES
            ('backend', 1), ('audio', 2), ('images', 4),
            ('translation', 5), ('highlighting', 6), ('storage', 7),
            ('processing', 8), ('api_keys', 9)
        ON CONFLICT DO NOTHING
    """)

    # ── 11. Config Validation Rules ───────────────────────────────
    op.create_table(
        "config_validation_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key_path", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("rule_value", sa.Text, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("is_warning", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE")),
    )
    op.create_index("idx_validation_key", "config_validation_rules", ["key_path"])

    # ── 12. Config Restart Log ────────────────────────────────────
    op.create_table(
        "config_restart_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("delay_seconds", sa.Integer, nullable=True),
        sa.Column("pre_restart_snapshot_id", sa.String(50), sa.ForeignKey("config_snapshots.snapshot_id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success", sa.Boolean, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("idx_restart_requested", "config_restart_log", [sa.text("requested_at DESC")])

    # ── 13. Bookmarks ─────────────────────────────────────────────
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("item_type", sa.String(50), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="time"),
        sa.Column("created_at", sa.Float, nullable=False),
        sa.Column("label", sa.Text, nullable=False, server_default="Bookmark"),
        sa.Column("position", sa.Float, nullable=True),
        sa.Column("sentence", sa.Integer, nullable=True),
        sa.Column("media_type", sa.String(50), nullable=True),
        sa.Column("media_id", sa.String(255), nullable=True),
        sa.Column("base_id", sa.String(255), nullable=True),
        sa.Column("segment_id", sa.String(255), nullable=True),
        sa.Column("chunk_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id", "user_id", "job_id"),
    )
    op.create_index("idx_bookmarks_user_job", "bookmarks", ["user_id", "job_id"])
    op.create_index("idx_bookmarks_created", "bookmarks", ["user_id", "job_id", sa.text("created_at DESC")])

    # ── 14. Resume Positions ──────────────────────────────────────
    op.create_table(
        "resume_positions",
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("job_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="time"),
        sa.Column("updated_at", sa.Float, nullable=False),
        sa.Column("position", sa.Float, nullable=True),
        sa.Column("sentence", sa.Integer, nullable=True),
        sa.Column("chunk_id", sa.String(255), nullable=True),
        sa.Column("media_type", sa.String(50), nullable=True),
        sa.Column("base_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "job_id"),
    )
    op.create_index("idx_resume_updated", "resume_positions", ["user_id", sa.text("updated_at DESC")])


def downgrade() -> None:
    op.drop_table("resume_positions")
    op.drop_table("bookmarks")
    op.drop_table("config_restart_log")
    op.drop_table("config_validation_rules")
    op.drop_table("config_group_settings")
    op.drop_table("config_secrets")
    op.drop_table("config_sensitive_keys")
    op.drop_table("config_audit_log")
    op.drop_table("config_snapshots")
    op.drop_table("library_item_grants")
    op.drop_table("books")
    op.drop_table("library_items")
    op.drop_table("sessions")
    op.drop_table("users")
