"""users.email and users.name nullable (schema drift fix)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)
    op.alter_column("users", "name", existing_type=sa.String(), nullable=True)


def downgrade():
    op.alter_column("users", "name", existing_type=sa.String(), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)