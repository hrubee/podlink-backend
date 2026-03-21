"""Add featured_videos to users

Revision ID: 909a58992ff0
Revises: b1c2d3e4f5a6
Create Date: 2026-03-21 16:39:23.293046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '909a58992ff0'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('featured_videos', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'featured_videos')
