"""remove the five pre-made sample folders when they are still empty and untouched

New accounts now start with only "Personal". For existing accounts, this deletes
Biology / Math 21 / Physics / Group Project / Workshops ONLY if the folder has no
items AND still has its original color and icon — anything the person has put
notes in, recolored or re-iconed is left alone.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# (name, color, icon) exactly as seeded/backfilled by migration 0008
SAMPLE_FOLDERS = [
    ("Biology", "#00674F", "leaf"),
    ("Math 21", "#009B77", "sigma"),
    ("Physics", "#046307", "atom"),
    ("Group Project", "#D4AF37", "users"),
    ("Workshops", "#7FE0A8", "wrench"),
]


def upgrade():
    bind = op.get_bind()
    for name, color, icon in SAMPLE_FOLDERS:
        bind.execute(
            sa.text(
                "DELETE FROM folders "
                "WHERE name = :name AND color = :color AND icon = :icon "
                "AND NOT EXISTS (SELECT 1 FROM items WHERE items.folder_id = folders.id)"
            ),
            {"name": name, "color": color, "icon": icon},
        )


def downgrade():
    # Deleted empty folders carry no data worth restoring.
    pass
