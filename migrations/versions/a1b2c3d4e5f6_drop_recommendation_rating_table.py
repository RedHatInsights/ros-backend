"""drop recommendation_rating table

Revision ID: a1b2c3d4e5f6
Revises: 52381cafc36f
Create Date: 2026-11-10 11:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '52381cafc36f'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('recommendation_rating')


def downgrade():
    op.create_table(
        'recommendation_rating',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('system_id', sa.Integer(), nullable=True),
        sa.Column('rated_by', sa.Text(), nullable=False),
        sa.Column('rating', sa.SmallInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['system_id'],
            ['systems.id'],
            name='recommendation_rating_system_id_fkey',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_recommendation_rating_rated_by'),
        'recommendation_rating',
        ['rated_by'],
        unique=False,
    )
    op.create_index(
        op.f('ix_recommendation_rating_system_id'),
        'recommendation_rating',
        ['system_id'],
        unique=False,
    )
