"""folders.icon + folders.position (customizable archive), default folders get theme colors/icons

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# (name, old seeded color, new theme color, icon, position)
DEFAULTS = [
    ("Biology", "#0E9F6E", "#00674F", "leaf", 0),
    ("Math 21", "#5B3FE0", "#009B77", "sigma", 1),
    ("Physics", "#E2456B", "#046307", "atom", 2),
    ("Group Project", "#A855F7", "#D4AF37", "users", 3),
    ("Workshops", "#D68A0C", "#7FE0A8", "wrench", 4),
    ("Personal", "#0891B2", "#2F9159", "user", 5),
]


def upgrade():
    op.add_column("folders", sa.Column("icon", sa.String(), nullable=True))
    op.add_column("folders", sa.Column("position", sa.Integer(), nullable=False, server_default="0"))

    # The app has always *displayed* the six default folders in the green theme
    # (a frontend lookup by name); store those values so the data matches what
    # people see and can now be edited.
    bind = op.get_bind()
    for name, old_color, new_color, icon, position in DEFAULTS:
        bind.execute(
            sa.text(
                "UPDATE folders SET icon = :icon, position = :position, "
                "color = CASE WHEN color = :old THEN :new ELSE color END "
                "WHERE name = :name"
            ),
            {"icon": icon, "position": position, "old": old_color, "new": new_color, "name": name},
        )
    # Any other folders sort after the defaults.
    bind.execute(sa.text("UPDATE folders SET position = 100 WHERE icon IS NULL"))


def downgrade():
    op.drop_column("folders", "position")
    op.drop_column("folders", "icon")
