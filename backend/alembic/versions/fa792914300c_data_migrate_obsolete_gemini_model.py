"""data_migrate_obsolete_gemini_model

Revision ID: fa792914300c
Revises: 6fb800001c1c
Create Date: 2026-10-11 05:34:59.562070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa792914300c'
down_revision: Union[str, None] = '6fb800001c1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Upgrade existing obsolete models to the supported version
    op.execute("UPDATE conversations SET ai_model = 'gemini-3.6-flash' WHERE ai_provider = 'gemini' AND ai_model = 'gemini-1.5-flash'")

def downgrade() -> None:
    pass
