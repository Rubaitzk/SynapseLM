"""Fix V2.1 constraints and enums

Revision ID: 6fb800001c1c
Revises: 1070bc8fa328
Create Date: 2026-10-10 17:07:53.810685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fb800001c1c'
down_revision: Union[str, None] = '1070bc8fa328'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add 'deleted' to Enum
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE lifecyclestate ADD VALUE IF NOT EXISTS 'deleted'")

    # 2. Change ON DELETE SET NULL to ON DELETE CASCADE
    op.drop_constraint('fk_conversations_parent_conversation_id', 'conversations', type_='foreignkey')
    op.create_foreign_key('fk_conversations_parent_conversation_id', 'conversations', 'conversations', ['parent_conversation_id'], ['id'], ondelete='CASCADE')

def downgrade() -> None:
    op.drop_constraint('fk_conversations_parent_conversation_id', 'conversations', type_='foreignkey')
    op.create_foreign_key('fk_conversations_parent_conversation_id', 'conversations', 'conversations', ['parent_conversation_id'], ['id'], ondelete='SET NULL')
    # Enums cannot be easily reversed to remove a value in Postgres, we will leave 'deleted' in the type.
