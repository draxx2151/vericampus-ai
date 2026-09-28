"""add_notifications_table

Revision ID: b3c4d5e6f7a8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-20 16:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('college_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=True),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('recipient_role', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['scholarship_applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_college_id'), 'notifications', ['college_id'], unique=False)
    op.create_index(op.f('ix_notifications_student_id'), 'notifications', ['student_id'], unique=False)
    op.create_index(op.f('ix_notifications_application_id'), 'notifications', ['application_id'], unique=False)
    op.create_index(op.f('ix_notifications_recipient_role'), 'notifications', ['recipient_role'], unique=False)
    op.create_index(op.f('ix_notifications_event_type'), 'notifications', ['event_type'], unique=False)
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_created_at'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_event_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_recipient_role'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_application_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_student_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_college_id'), table_name='notifications')
    op.drop_table('notifications')
