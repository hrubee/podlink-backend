"""add subscription columns to users

Revision ID: b1c2d3e4f5a6
Revises: 374e8ad2387d
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

revision = 'b1c2d3e4f5a6'
down_revision = '374e8ad2387d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add subscription_status if not exists
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='subscription_status'"
    ))
    if not result.fetchone():
        op.add_column('users', sa.Column(
            'subscription_status', sa.String(), nullable=True, server_default='free'
        ))
        conn.execute(sa.text("UPDATE users SET subscription_status = 'free' WHERE subscription_status IS NULL"))

    # Add subscription_ends_at if not exists
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' AND column_name='subscription_ends_at'"
    ))
    if not result.fetchone():
        op.add_column('users', sa.Column(
            'subscription_ends_at', sa.DateTime(timezone=True), nullable=True
        ))


def downgrade() -> None:
    op.drop_column('users', 'subscription_ends_at')
    op.drop_column('users', 'subscription_status')
