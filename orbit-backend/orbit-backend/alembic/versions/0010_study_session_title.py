"""study_sessions.title — what was studied, so Insights can show top subjects

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("study_sessions", sa.Column("title", sa.String(), nullable=True))


def downgrade():
    op.drop_column("study_sessions", "title")
