"""Initial schema with pgvector (1024-dim embeddings)."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # JSON embeddings — works without the pgvector Postgres extension (local Windows).
    embedding_col = postgresql.JSON()

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("whatsapp_number", sa.String(20), nullable=False),
        sa.Column("language_preference", sa.String(8), server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_whatsapp_number", "users", ["whatsapp_number"], unique=True)

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("verdict", sa.String(32), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("explanation_en", sa.Text(), nullable=True),
        sa.Column("explanation_ur", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSON(), nullable=True),
        sa.Column("language", sa.String(8), server_default="en"),
        sa.Column("trend_score", sa.Float(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("embedding", embedding_col, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_claims_content_hash", "claims", ["content_hash"])
    op.create_index(
        "ix_claims_feed",
        "claims",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
        postgresql_where=sa.text("verdict IS NOT NULL"),
    )

    op.create_table(
        "scam_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_text", sa.Text(), nullable=False),
        sa.Column("scam_type", sa.String(64), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ur", sa.Text(), nullable=True),
        sa.Column("embedding", embedding_col, nullable=True),
        sa.Column("times_reported", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "scam_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("submitted_text", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("scam_type", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("risk_verdict", sa.String(32), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("explanation_en", sa.Text(), nullable=True),
        sa.Column("explanation_ur", sa.Text(), nullable=True),
        sa.Column("red_flags", postgresql.JSON(), nullable=True),
        sa.Column("sender_identifier", sa.String(128), nullable=True),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("embedding", embedding_col, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_scam_reports_content_hash", "scam_reports", ["content_hash"])

    op.create_table(
        "media_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("authenticity_score", sa.Float(), nullable=True),
        sa.Column("signals", postgresql.JSON(), nullable=True),
        sa.Column("verdict", sa.String(32), nullable=True),
        sa.Column("explanation_en", sa.Text(), nullable=True),
        sa.Column("explanation_ur", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_media_checks_file_hash", "media_checks", ["file_hash"])

    op.create_table(
        "agent_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("parent_check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_check_type", sa.String(32), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("input_summary", sa.String(1024), nullable=True),
        sa.Column("output_summary", sa.String(1024), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("raw_output", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_logs_parent_check_id", "agent_logs", ["parent_check_id"])

    op.create_table(
        "trend_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("report_volume", sa.Integer(), server_default="0"),
        sa.Column("spread_score", sa.Float(), server_default="0"),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_trend_snapshots_related_entity_id", "trend_snapshots", ["related_entity_id"])

    op.create_table(
        "curated_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(1024), nullable=False, unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("publisher", sa.String(256), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ur", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "media_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("media_check_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_checks.id"), nullable=True),
        sa.Column("phash", sa.String(64), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("embedding", embedding_col, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_media_fingerprints_phash", "media_fingerprints", ["phash"])
    op.create_index("ix_media_fingerprints_media_check_id", "media_fingerprints", ["media_check_id"])


def downgrade() -> None:
    op.drop_table("media_fingerprints")
    op.drop_table("curated_references")
    op.drop_table("trend_snapshots")
    op.drop_table("agent_logs")
    op.drop_table("media_checks")
    op.drop_table("scam_reports")
    op.drop_table("scam_patterns")
    op.drop_table("claims")
    op.drop_table("users")
