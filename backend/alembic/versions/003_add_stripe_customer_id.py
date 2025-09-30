"""add stripe_customer_id to users

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # stripe_customer_id カラムを追加
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))
    
    # ユニーク制約を追加
    op.create_unique_constraint('uq_users_stripe_customer_id', 'users', ['stripe_customer_id'])


def downgrade():
    # ユニーク制約を削除
    op.drop_constraint('uq_users_stripe_customer_id', 'users', type_='unique')
    
    # カラムを削除
    op.drop_column('users', 'stripe_customer_id')
