"""google calendar sync: events.google_event_id + google_connections

(Task deadlines reuse the existing tasks.due_date text column — it now holds
"YYYY-MM-DD" or "" — so they need no schema change.)

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("events", sa.Column("google_event_id", sa.String(), nullable=True))
    op.create_table(
        "google_connections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_enc", sa.String(), nullable=False),
        sa.Column("google_email", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("needs_reauth", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_google_connections_user_id", "google_connections", ["user_id"], unique=True)


def downgrade():
    op.drop_index("ix_google_connections_user_id", table_name="google_connections")
    op.drop_table("google_connections")
    op.drop_column("events", "google_event_id")
