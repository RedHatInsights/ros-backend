"""remove columns from systems

Revision ID: 26a16593ec96
Revises: 3d3a1981593c
Create Date: 2022-03-24 01:24:52.670825

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '26a16593ec96'
down_revision = '3d3a1981593c'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('systems', 'rule_hit_details')
    op.drop_column('systems', 'number_of_recommendations')


def downgrade():
    op.add_column(
        'systems',
        sa.Column('rule_hit_details',
                  JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        'systems',
        sa.Column('number_of_recommendations',
                  sa.Integer(), nullable=True))
