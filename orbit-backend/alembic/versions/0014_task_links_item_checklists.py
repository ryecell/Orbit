"""task links to archive + checklists inside items

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "checklist_entries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_checklist_entries_item_id", "checklist_entries", ["item_id"])

    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("folder_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("item_id", sa.String(), nullable=True))
        batch.create_foreign_key("fk_tasks_folder_id", "folders", ["folder_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_tasks_item_id", "items", ["item_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_tasks_folder_id", ["folder_id"])
        batch.create_index("ix_tasks_item_id", ["item_id"])


def downgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_item_id")
        batch.drop_index("ix_tasks_folder_id")
        batch.drop_constraint("fk_tasks_item_id", type_="foreignkey")
        batch.drop_constraint("fk_tasks_folder_id", type_="foreignkey")
        batch.drop_column("item_id")
        batch.drop_column("folder_id")
    op.drop_table("checklist_entries")
