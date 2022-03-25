"""drop_columns_from_systems

Revision ID: 17a0c64e29e0
Revises: 7883d9fe07b0
Create Date: 2022-03-18 23:21:07.130646

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '17a0c64e29e0'
down_revision = '7883d9fe07b0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('systems', 'rule_hit_details')
    op.drop_column('systems', 'number_of_recommendations')


def downgrade():
    op.add_column('systems', sa.Column('number_of_recommendations', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('systems', sa.Column('rule_hit_details', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
