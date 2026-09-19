"""create business data schema

Revision ID: 001_create_business_data_schema
Revises: 
Create Date: 2026-09-17 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_create_business_data_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Merchants Table
    op.create_table(
        'merchants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('shop_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )
    op.create_index(op.f('ix_merchants_phone'), 'merchants', ['phone'], unique=True)

    # 2. Products Table
    op.create_table(
        'products',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('cost_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('reorder_level', sa.Integer(), nullable=False),
        sa.Column('supplier', sa.String(length=255), nullable=True),
        sa.Column('average_daily_sales', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_merchant_id'), 'products', ['merchant_id'], unique=False)

    # 3. Inventory Table
    op.create_table(
        'inventory',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('reorder_level', sa.Integer(), nullable=False),
        sa.Column('maximum_stock', sa.Integer(), nullable=False),
        sa.Column('last_restocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('current_stock >= 0', name='chk_inventory_stock_non_negative'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id')
    )
    op.create_index(op.f('ix_inventory_product_id'), 'inventory', ['product_id'], unique=True)

    # 4. Customers Table
    op.create_table(
        'customers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('total_spend', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('purchase_count', sa.Integer(), nullable=False),
        sa.Column('last_purchase_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_purchase_interval', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_merchant_id'), 'customers', ['merchant_id'], unique=False)

    # 5. Transactions Table
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=20), nullable=False),
        sa.Column('transaction_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_customer_id'), 'transactions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_transactions_merchant_id'), 'transactions', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_transactions_product_id'), 'transactions', ['product_id'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_timestamp'), 'transactions', ['transaction_timestamp'], unique=False)
    op.create_index('idx_transactions_merchant_timestamp', 'transactions', ['merchant_id', 'transaction_timestamp'], unique=False)
    op.create_index('idx_transactions_merchant_product_timestamp', 'transactions', ['merchant_id', 'product_id', 'transaction_timestamp'], unique=False)

    # 6. Business Events Table
    op.create_table(
        'business_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_business_events_detected_at'), 'business_events', ['detected_at'], unique=False)
    op.create_index(op.f('ix_business_events_event_type'), 'business_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_business_events_merchant_id'), 'business_events', ['merchant_id'], unique=False)

    # 7. Recommendations Table
    op.create_table(
        'recommendations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('urgency', sa.String(length=20), nullable=False),
        sa.Column('expected_impact', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['business_events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendations_event_id'), 'recommendations', ['event_id'], unique=False)
    op.create_index(op.f('ix_recommendations_merchant_id'), 'recommendations', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_recommendations_status'), 'recommendations', ['status'], unique=False)

    # 8. Actions Table
    op.create_table(
        'actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('recommendation_id', sa.String(length=36), nullable=True),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_actions_merchant_id'), 'actions', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_actions_recommendation_id'), 'actions', ['recommendation_id'], unique=False)
    op.create_index(op.f('ix_actions_status'), 'actions', ['status'], unique=False)

    # 9. Outcomes Table
    op.create_table(
        'outcomes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('action_id', sa.String(length=36), nullable=False),
        sa.Column('sales_before', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('sales_after', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('revenue_change', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('stockout_prevented', sa.Boolean(), nullable=False),
        sa.Column('customers_recovered', sa.Integer(), nullable=False),
        sa.Column('offer_conversion', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('impact', sa.Text(), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['action_id'], ['actions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('action_id')
    )
    op.create_index(op.f('ix_outcomes_action_id'), 'outcomes', ['action_id'], unique=True)


def downgrade() -> None:
    op.drop_table('outcomes')
    op.drop_table('actions')
    op.drop_table('recommendations')
    op.drop_table('business_events')
    op.drop_table('transactions')
    op.drop_table('customers')
    op.drop_table('inventory')
    op.drop_table('products')
    op.drop_table('merchants')
