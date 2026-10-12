"""add cancelled status to invitations

Revision ID: a81f3d9b4c2e
Revises: 7cd4024dc35b
Create Date: 2026-10-12 00:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a81f3d9b4c2e'
down_revision: Union[str, None] = '7cd4024dc35b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE invitationstatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # Postgres enum values cannot be easily dropped without recreating the type
    pass
