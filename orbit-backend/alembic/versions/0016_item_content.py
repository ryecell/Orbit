"""archive item notes/content (text the study AI features read)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("items", sa.Column("content", sa.Text(), nullable=True, server_default=""))


def downgrade():
    op.drop_column("items", "content")
