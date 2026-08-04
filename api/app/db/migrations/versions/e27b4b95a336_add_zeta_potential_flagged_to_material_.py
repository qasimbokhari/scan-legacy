"""add_zeta_potential_flagged_to_material_records

Revision ID: e27b4b95a336
Revises: 40200d40ce1e
Create Date: 2026-08-04 19:29:24.159750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e27b4b95a336'
down_revision: Union[str, Sequence[str], None] = '40200d40ce1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('material_records', sa.Column('zeta_potential_flagged', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('material_records', 'zeta_potential_flagged')
