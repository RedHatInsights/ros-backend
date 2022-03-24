"""alter pk on performance profile

Revision ID: 77fdc857c94f
Revises: ccf59577aca2
Create Date: 2022-03-25 01:18:21.000251

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77fdc857c94f'
down_revision = 'ccf59577aca2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'ALTER TABLE performance_profile DROP '
        ' CONSTRAINT performance_profile_pkey'
    )
    op.create_primary_key(
        'performance_profile_pkey',
        'performance_profile',
        ['system_id']
    )


def downgrade():
    op.execute(
        'ALTER TABLE performance_profile DROP '
        ' CONSTRAINT performance_profile_pkey'
    )
    op.create_primary_key(
        'performance_profile_pkey',
        'performance_profile',
        ['system_id', 'report_date']
    )
