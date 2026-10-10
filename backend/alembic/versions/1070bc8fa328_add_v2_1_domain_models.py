"""Add V2.1 domain models

Revision ID: 1070bc8fa328
Revises: 137d5e9a8f95
Create Date: 2026-10-10 16:40:04.327655

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1070bc8fa328'
down_revision: Union[str, None] = '137d5e9a8f95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Enum types
    lifecycle_state = postgresql.ENUM('active', 'archived', name='lifecyclestate')
    lifecycle_state.create(op.get_bind(), checkfirst=True)

    # 2. Alter `conversations`
    op.add_column('conversations', sa.Column('parent_conversation_id', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('snapshot_sequence_id', sa.Integer(), nullable=True))
    op.add_column('conversations', sa.Column('lifecycle_state', lifecycle_state, server_default='active', nullable=False))
    
    op.create_foreign_key('fk_conversations_parent_conversation_id', 'conversations', 'conversations', ['parent_conversation_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_conversations_parent_conversation_id'), 'conversations', ['parent_conversation_id'], unique=False)

    # 3. Add `sequence_id` to `messages`
    op.execute("CREATE SEQUENCE IF NOT EXISTS messages_sequence_id_seq")
    op.add_column('messages', sa.Column('sequence_id', sa.Integer(), server_default=sa.text("nextval('messages_sequence_id_seq')"), nullable=False))
    op.create_index(op.f('ix_messages_sequence_id'), 'messages', ['sequence_id'], unique=True)

    # 4. Create `conversation_shares`
    op.create_table('conversation_shares',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('conversation_id', sa.String(), nullable=False),
    sa.Column('token_hash', sa.String(), nullable=False),
    sa.Column('created_by', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_shares_conversation_id'), 'conversation_shares', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_shares_id'), 'conversation_shares', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_shares_token_hash'), 'conversation_shares', ['token_hash'], unique=True)

    # 5. Create `conversation_access_requests`
    request_status = sa.Enum('pending', 'accepted', 'rejected', 'cancelled', name='requeststatus')
    
    op.create_table('conversation_access_requests',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('share_id', sa.String(), nullable=False),
    sa.Column('requester_id', sa.String(), nullable=False),
    sa.Column('branch_conversation_id', sa.String(), nullable=False),
    sa.Column('status', request_status, server_default='pending', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['branch_conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['share_id'], ['conversation_shares.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_access_requests_branch_conversation_id'), 'conversation_access_requests', ['branch_conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_access_requests_id'), 'conversation_access_requests', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_access_requests_requester_id'), 'conversation_access_requests', ['requester_id'], unique=False)
    op.create_index(op.f('ix_conversation_access_requests_share_id'), 'conversation_access_requests', ['share_id'], unique=False)
    op.create_index('ix_uq_pending_request', 'conversation_access_requests', ['share_id', 'requester_id'], unique=True, postgresql_where=sa.text("status = 'pending'"))


def downgrade() -> None:
    # 1. Drop `conversation_access_requests`
    op.drop_index('ix_uq_pending_request', table_name='conversation_access_requests', postgresql_where=sa.text("status = 'pending'"))
    op.drop_index(op.f('ix_conversation_access_requests_share_id'), table_name='conversation_access_requests')
    op.drop_index(op.f('ix_conversation_access_requests_requester_id'), table_name='conversation_access_requests')
    op.drop_index(op.f('ix_conversation_access_requests_id'), table_name='conversation_access_requests')
    op.drop_index(op.f('ix_conversation_access_requests_branch_conversation_id'), table_name='conversation_access_requests')
    op.drop_table('conversation_access_requests')

    # Drop the enum
    op.execute("DROP TYPE IF EXISTS requeststatus")

    # 2. Drop `conversation_shares`
    op.drop_index(op.f('ix_conversation_shares_token_hash'), table_name='conversation_shares')
    op.drop_index(op.f('ix_conversation_shares_id'), table_name='conversation_shares')
    op.drop_index(op.f('ix_conversation_shares_conversation_id'), table_name='conversation_shares')
    op.drop_table('conversation_shares')

    # 3. Drop `sequence_id` from `messages`
    op.drop_index(op.f('ix_messages_sequence_id'), table_name='messages')
    op.drop_column('messages', 'sequence_id')
    op.execute("DROP SEQUENCE IF EXISTS messages_sequence_id_seq")

    # 4. Alter `conversations`
    op.drop_index(op.f('ix_conversations_parent_conversation_id'), table_name='conversations')
    op.drop_constraint('fk_conversations_parent_conversation_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'lifecycle_state')
    op.drop_column('conversations', 'snapshot_sequence_id')
    op.drop_column('conversations', 'parent_conversation_id')
    
    # Drop the enum
    op.execute("DROP TYPE IF EXISTS lifecyclestate")
