"""add cancel_at_period_end to subscriptions

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # cancel_at_period_end カラムを追加
    op.add_column('subscriptions', sa.Column('cancel_at_period_end', sa.Boolean(), nullable=True))
    
    # デフォルト値をFalseに設定
    op.execute("UPDATE subscriptions SET cancel_at_period_end = FALSE WHERE cancel_at_period_end IS NULL")


def downgrade():
    # カラムを削除
    op.drop_column('subscriptions', 'cancel_at_period_end')
