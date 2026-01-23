"""Create organizations table

Revision ID: cb5f73662c80
Revises: 
Create Date: 2026-01-22 23:53:16.050380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb5f73662c80'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the organizations table."""
    op.create_table(
        'organizations',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('admin', sa.String(), nullable=False),
        sa.Column('cross_match_trait', sa.String(), nullable=True),
        sa.CheckConstraint('length(admin) > 0', name='organizations_admin_check'),
        sa.PrimaryKeyConstraint('name')
    )


def downgrade() -> None:
    """Drop the organizations table."""
    op.drop_table('organizations')
