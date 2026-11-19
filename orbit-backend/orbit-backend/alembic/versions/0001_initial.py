"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-11

Hand-written to match models.py as of this commit, rather than generated
via `alembic revision --autogenerate` against a live database. If your
actual schema ever drifts from models.py, regenerate this with autogenerate
against a real Postgres instance instead of trusting this file blindly.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("verification_token", sa.String(), nullable=True),
        sa.Column("verification_expires", sa.DateTime(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(), primary_key=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "folders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("folder_id", sa.String(), sa.ForeignKey("folders.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=True),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    )

    op.create_table(
        "group_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("sender_name", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_group_messages_group_id", "group_messages", ["group_id"])


def downgrade():
    op.drop_table("group_messages")
    op.drop_table("reminders")
    op.drop_table("tasks")
    op.drop_table("items")
    op.drop_table("folders")
    op.drop_table("revoked_tokens")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
