"""initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2024-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'initial_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create wiki_entries table
    op.create_table('wiki_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('modified_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wiki_entries_title'), 'wiki_entries', ['title'], unique=True)

    # Create wiki_entry_logs table
    op.create_table('wiki_entry_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wiki_entry_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_time', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('cache_hit', sa.Boolean(), nullable=False),
        sa.Column('needed_update', sa.Boolean(), nullable=False),
        sa.Column('was_updated', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['wiki_entry_id'], ['wiki_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('wiki_entry_logs')
    op.drop_index(op.f('ix_wiki_entries_title'), table_name='wiki_entries')
    op.drop_table('wiki_entries')
