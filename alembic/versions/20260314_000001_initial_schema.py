from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_preview", sa.Text(), nullable=False, server_default=""),
        sa.Column("sender", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("sender_domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_headers", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index("ix_emails_message_id", "emails", ["message_id"], unique=True)

    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scanned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phishing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=True),
        sa.Column("phishing_probability", sa.Float(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(length=50), nullable=False, server_default="LEGITIMATE"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="LOW"),
        sa.Column("reasons", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("spf_status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("dkim_status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_id", name="uq_scan_results_email_id"),
    )
    op.create_index("ix_scan_results_email_id", "scan_results", ["email_id"], unique=False)
    op.create_index("ix_scan_results_scan_run_id", "scan_results", ["scan_run_id"], unique=False)
    op.create_index("ix_scan_results_scanned_at", "scan_results", ["scanned_at"], unique=False)

    op.create_table(
        "url_findings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_result_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("suspicious", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["scan_result_id"], ["scan_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_url_findings_scan_result_id", "url_findings", ["scan_result_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_url_findings_scan_result_id", table_name="url_findings")
    op.drop_table("url_findings")
    op.drop_index("ix_scan_results_scanned_at", table_name="scan_results")
    op.drop_index("ix_scan_results_scan_run_id", table_name="scan_results")
    op.drop_index("ix_scan_results_email_id", table_name="scan_results")
    op.drop_table("scan_results")
    op.drop_table("scan_runs")
    op.drop_index("ix_emails_message_id", table_name="emails")
    op.drop_table("emails")
