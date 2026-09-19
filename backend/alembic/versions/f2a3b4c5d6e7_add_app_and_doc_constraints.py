"""add_app_and_doc_constraints

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-19 19:31:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add unique constraint for student_id on scholarship_applications
    op.create_unique_constraint(
        'uq_scholarship_applications_student_id',
        'scholarship_applications',
        ['student_id']
    )
    # 2. Add unique constraint for (application_id, document_type) on documents
    op.create_unique_constraint(
        'uq_documents_app_doc_type',
        'documents',
        ['application_id', 'document_type']
    )


def downgrade() -> None:
    op.drop_constraint('uq_documents_app_doc_type', 'documents', type_='unique')
    op.drop_constraint('uq_scholarship_applications_student_id', 'scholarship_applications', type_='unique')
