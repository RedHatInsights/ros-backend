"""create performance profile history

Revision ID: 8c6f4554d24d
Revises: 26a16593ec96
Create Date: 2022-03-24 13:39:41.695476

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8c6f4554d24d'
down_revision = '26a16593ec96'
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.execute(
            'CREATE TABLE performance_profile_history AS TABLE performance_profile'
        )
    except Exception as err:
        print(
            "Failed to create performance_profile_history with error=%s",
            err
        )
        raise


def downgrade():
    op.drop_table('performance_profile_history')
