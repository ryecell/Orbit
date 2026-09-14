"""add password reset fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("reset_token", sa.String(), nullable=True))
    op.add_column("users", sa.Column("reset_expires", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("sessions_invalidated_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("users", "sessions_invalidated_at")
    op.drop_column("users", "reset_expires")
    op.drop_column("users", "reset_token")
