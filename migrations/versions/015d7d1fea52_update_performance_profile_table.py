"""update performance profile table

Revision ID: 015d7d1fea52
Revises: 605a688d0cd2
Create Date: 2022-03-23 15:48:26.160344

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '015d7d1fea52'
down_revision = '605a688d0cd2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'performance_profile',
        sa.Column('number_of_recommendations', sa.Integer(), nullable=True))
    op.add_column(
        'performance_profile',
        sa.Column('state', sa.String(length=25), nullable=True))
    op.add_column(
        'performance_profile',
        sa.Column('operating_system',
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        'performance_profile',
        sa.Column('rule_hit_details',
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column(
        'performance_profile', 'report_date',
        existing_type=sa.Date(), type_=sa.DateTime(timezone=True))


def downgrade():
    op.drop_column('performance_profile', 'number_of_recommendations')
    op.drop_column('performance_profile', 'state')
    op.drop_column('performance_profile', 'operating_system')
    op.drop_column('performance_profile', 'rule_hit_details')
    op.alter_column(
        'performance_profile', 'report_date',
        existing_type=sa.DateTime(timezone=True), type_=sa.Date())
