"""account deletion support: users.deleted_at, group_messages.sender_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    with op.batch_alter_table("group_messages") as batch:
        batch.add_column(sa.Column("sender_id", sa.String(), nullable=True))
        batch.create_index("ix_group_messages_sender_id", ["sender_id"])
        batch.create_foreign_key(
            "fk_group_messages_sender_id_users", "users", ["sender_id"], ["id"], ondelete="SET NULL"
        )


def downgrade():
    with op.batch_alter_table("group_messages") as batch:
        batch.drop_constraint("fk_group_messages_sender_id_users", type_="foreignkey")
        batch.drop_index("ix_group_messages_sender_id")
        batch.drop_column("sender_id")

    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_at")
