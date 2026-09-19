"""add_admin_setup_code_and_nullable_college_code

Revision ID: e1f2a3b4c5d6
Revises: d0c676a58d4b
Create Date: 2026-09-19 18:32:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0c676a58d4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add admin_setup_code and is_setup_code_used columns to colleges table
    op.add_column('colleges', sa.Column('admin_setup_code', sa.String(length=100), nullable=True))
    op.add_column('colleges', sa.Column('is_setup_code_used', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index(op.f('ix_colleges_admin_setup_code'), 'colleges', ['admin_setup_code'], unique=True)
    
    # Make college_code nullable
    op.alter_column('colleges', 'college_code', existing_type=sa.String(length=100), nullable=True)


def downgrade() -> None:
    op.alter_column('colleges', 'college_code', existing_type=sa.String(length=100), nullable=False)
    op.drop_index(op.f('ix_colleges_admin_setup_code'), table_name='colleges')
    op.drop_column('colleges', 'is_setup_code_used')
    op.drop_column('colleges', 'admin_setup_code')
