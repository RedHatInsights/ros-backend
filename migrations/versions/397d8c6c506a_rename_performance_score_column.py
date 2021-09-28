"""rename performance_score column

Revision ID: 397d8c6c506a
Revises: e67b2b19df0e
Create Date: 2021-09-13 00:17:30.617007

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '397d8c6c506a'
down_revision = 'e67b2b19df0e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'performance_profile', 'performance_score',
        new_column_name='performance_utilization'
    )

def downgrade():
    op.alter_column(
        'performance_profile', 'performance_utilization',
        new_column_name='performance_score')
