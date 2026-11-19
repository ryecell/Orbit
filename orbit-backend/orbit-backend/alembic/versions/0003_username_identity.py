"""username as primary identifier, email/name become optional

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-14

Backfills a username for any pre-existing rows (e.g. test accounts created
before this migration existed) from their email's local part, falling back
to a slice of their id if there's no email. A short id suffix is appended
to avoid collisions between two users who happen to share an email prefix.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

users_table = sa.table(
    "users",
    sa.column("id", sa.String),
    sa.column("email", sa.String),
    sa.column("username", sa.String),
)


def upgrade():
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)
    op.alter_column("users", "name", existing_type=sa.String(), nullable=True)

    conn = op.get_bind()
    existing = conn.execute(
        sa.select(users_table.c.id, users_table.c.email).where(users_table.c.username.is_(None))
    ).fetchall()
    for row in existing:
        base = (row.email.split("@")[0] if row.email else row.id[:8]).lower()
        fallback_username = f"{base}-{row.id[:4]}"
        conn.execute(
            users_table.update().where(users_table.c.id == row.id).values(username=fallback_username)
        )

    op.alter_column("users", "username", existing_type=sa.String(), nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"])


def downgrade():
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
    op.alter_column("users", "name", existing_type=sa.String(), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)
