"""add_multi_college_support

Revision ID: d0c676a58d4b
Revises: '2416706cec79'
Create Date: 2026-09-19 11:26:46.523261

"""
import uuid
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd0c676a58d4b'
down_revision: Union[str, None] = '2416706cec79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create colleges table
    op.create_table(
        'colleges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('college_name', sa.String(length=255), nullable=False),
        sa.Column('college_code', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_colleges_college_code'), 'colleges', ['college_code'], unique=True)

    # 2. Add nullable college_id columns to admin_officers and students
    op.add_column('admin_officers', sa.Column('college_id', sa.UUID(), nullable=True))
    op.add_column('students', sa.Column('college_id', sa.UUID(), nullable=True))

    # 3. Seed default college if existing records exist
    conn = op.get_bind()
    default_college_id = uuid.uuid4()
    
    # Check if we have any existing students or admins
    has_students = conn.execute(sa.text("SELECT COUNT(*) FROM students")).scalar() > 0
    has_admins = conn.execute(sa.text("SELECT COUNT(*) FROM admin_officers")).scalar() > 0

    if has_students or has_admins:
        conn.execute(
            sa.text("""
                INSERT INTO colleges (id, college_name, college_code, email, is_active, created_at, updated_at)
                VALUES (:id, 'Demo Engineering College', 'DEMO001', 'info@demo001.edu', true, NOW(), NOW())
                ON CONFLICT (college_code) DO NOTHING
            """),
            {"id": default_college_id}
        )
        # Fetch actual college id for DEMO001
        res = conn.execute(sa.text("SELECT id FROM colleges WHERE college_code = 'DEMO001'")).first()
        if res:
            actual_college_id = res[0]
            conn.execute(sa.text("UPDATE students SET college_id = :c_id WHERE college_id IS NULL"), {"c_id": actual_college_id})
            conn.execute(sa.text("UPDATE admin_officers SET college_id = :c_id WHERE college_id IS NULL"), {"c_id": actual_college_id})

    # 4. Enforce NOT NULL constraints
    op.alter_column('admin_officers', 'college_id', existing_type=sa.UUID(), nullable=False)
    op.alter_column('students', 'college_id', existing_type=sa.UUID(), nullable=False)

    # 5. Add unique & foreign key constraints with explicit names
    op.create_unique_constraint('uq_admin_officers_college_id', 'admin_officers', ['college_id'])
    op.create_foreign_key('fk_admin_officers_college_id', 'admin_officers', 'colleges', ['college_id'], ['id'])
    op.create_foreign_key('fk_students_college_id', 'students', 'colleges', ['college_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_students_college_id', 'students', type_='foreignkey')
    op.drop_column('students', 'college_id')

    op.drop_constraint('fk_admin_officers_college_id', 'admin_officers', type_='foreignkey')
    op.drop_constraint('uq_admin_officers_college_id', 'admin_officers', type_='unique')
    op.drop_column('admin_officers', 'college_id')

    op.drop_index(op.f('ix_colleges_college_code'), table_name='colleges')
    op.drop_table('colleges')
