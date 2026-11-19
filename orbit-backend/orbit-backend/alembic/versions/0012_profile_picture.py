"""profile pictures: users.avatar (small JPEG) + users.avatar_updated_at

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-28

"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("avatar", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("avatar_updated_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar")
