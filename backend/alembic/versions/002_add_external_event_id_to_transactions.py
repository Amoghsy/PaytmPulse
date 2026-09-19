"""add external_event_id to transactions

Revision ID: 002_add_external_event_id
Revises: 001_create_business_data_schema
Create Date: 2026-09-17 23:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_external_event_id'
down_revision: Union[str, None] = '001_create_business_data_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('external_event_id', sa.String(length=100), nullable=True))
    op.create_index('ix_transactions_external_event_id', 'transactions', ['external_event_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_transactions_external_event_id', table_name='transactions')
    op.drop_column('transactions', 'external_event_id')
