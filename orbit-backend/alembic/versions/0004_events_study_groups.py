"""add events, study sessions, and real group membership

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    )

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("invite_code", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint("uq_groups_invite_code", "groups", ["invite_code"])
    op.create_index("ix_groups_invite_code", "groups", ["invite_code"])

    op.create_table(
        "group_memberships",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("group_id", sa.String(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_group_memberships_group_id", "group_memberships", ["group_id"])
    op.create_index("ix_group_memberships_user_id", "group_memberships", ["user_id"])
    op.create_unique_constraint("uq_group_membership", "group_memberships", ["group_id", "user_id"])

    # group_messages.group_id used to be a free-standing string — there was
    # no Group table yet, every user shared one hardcoded room ID. Clear out
    # any messages that don't correspond to a real group before adding the
    # foreign key, since orphaned rows would fail the constraint. This
    # table should be empty on any Neon-era deploy, but it's a cheap safety
    # net either way.
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM group_messages WHERE group_id NOT IN (SELECT id FROM groups)"))
    op.create_foreign_key("fk_group_messages_group_id", "group_messages", "groups", ["group_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_group_messages_group_id", "group_messages", type_="foreignkey")
    op.drop_table("group_memberships")
    op.drop_index("ix_groups_invite_code", table_name="groups")
    op.drop_constraint("uq_groups_invite_code", "groups", type_="unique")
    op.drop_table("groups")
    op.drop_table("study_sessions")
    op.drop_table("events")
