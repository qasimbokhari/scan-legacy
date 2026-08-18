"""add_nanoreg_records_table

Revision ID: add_nanoreg_records
Revises: add_analyte_compounds
Create Date: 2026-08-18

Adds nanoreg_records table for ENANOMAPPER complex metrics from NanoReg and NanoReg2 dumps.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_nanoreg_records'
down_revision: Union[str, Sequence[str], None] = 'add_analyte_compounds'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('nanoreg_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('substance_name', sa.String(), nullable=False),
    sa.Column('jrc_id', sa.String(), nullable=True),
    sa.Column('topcategory', sa.String(), nullable=True),
    sa.Column('endpointcategory', sa.String(), nullable=True),
    sa.Column('endpoint', sa.String(), nullable=True),
    sa.Column('value_numeric', sa.Float(), nullable=True),
    sa.Column('unit', sa.String(), nullable=True),
    sa.Column('text_value', sa.String(), nullable=True),
    sa.Column('reference', sa.String(), nullable=True),
    sa.Column('source_type', sa.String(), nullable=False),
    sa.Column('provenance_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('nanoreg_records')
