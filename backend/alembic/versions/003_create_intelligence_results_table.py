"""create intelligence_results table

Revision ID: 003_create_intelligence_results
Revises: 002_add_external_event_id
Create Date: 2026-09-17 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_create_intelligence_results'
down_revision: Union[str, None] = '002_add_external_event_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'intelligence_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=True),
        sa.Column('result_type', sa.String(length=50), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['business_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_intelligence_results_merchant_id', 'intelligence_results', ['merchant_id'], unique=False)
    op.create_index('ix_intelligence_results_event_id', 'intelligence_results', ['event_id'], unique=False)
    op.create_index('ix_intelligence_results_result_type', 'intelligence_results', ['result_type'], unique=False)
    op.create_index('ix_intelligence_results_created_at', 'intelligence_results', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_intelligence_results_created_at', table_name='intelligence_results')
    op.drop_index('ix_intelligence_results_result_type', table_name='intelligence_results')
    op.drop_index('ix_intelligence_results_event_id', table_name='intelligence_results')
    op.drop_index('ix_intelligence_results_merchant_id', table_name='intelligence_results')
    op.drop_table('intelligence_results')
