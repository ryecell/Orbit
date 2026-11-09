"""grades tracker

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "grade_settings",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("scale", sa.String(), nullable=False),
        sa.Column("passing_percent", sa.Float(), nullable=False, server_default="75"),
        sa.Column("table_json", sa.Text(), nullable=True),
    )
    op.create_table(
        "grade_subjects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("units", sa.Float(), nullable=False, server_default="1"),
        sa.Column("folder_id", sa.String(), sa.ForeignKey("folders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("final_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_grade_subjects_owner_id", "grade_subjects", ["owner_id"])
    op.create_table(
        "grade_categories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("subject_id", sa.String(), sa.ForeignKey("grade_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_grade_categories_subject_id", "grade_categories", ["subject_id"])
    op.create_table(
        "grade_entries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("subject_id", sa.String(), sa.ForeignKey("grade_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(), sa.ForeignKey("grade_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_grade_entries_subject_id", "grade_entries", ["subject_id"])


def downgrade():
    op.drop_table("grade_entries")
    op.drop_table("grade_categories")
    op.drop_table("grade_subjects")
    op.drop_table("grade_settings")
