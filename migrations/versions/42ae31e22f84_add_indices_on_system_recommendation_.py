"""Add indices on system, recommendation_rating, performance_profile_history

Revision ID: 42ae31e22f84
Revises: 3fb61393a227
Create Date: 2023-03-03 11:28:23.004229

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42ae31e22f84'
down_revision = '3fb61393a227'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_performance_profile_state'), 'performance_profile', ['state'], unique=False)
    op.create_index('non_optimized_system_profiles', 'performance_profile', ['number_of_recommendations'], unique=False, postgresql_where=sa.text('number_of_recommendations > 0'))
    op.create_index(op.f('ix_performance_profile_history_report_date'), 'performance_profile_history', ['report_date'], unique=False)
    op.create_index(op.f('ix_recommendation_rating_rated_by'), 'recommendation_rating', ['rated_by'], unique=False)
    op.create_index(op.f('ix_recommendation_rating_system_id'), 'recommendation_rating', ['system_id'], unique=False)
    op.create_index('inventory_id_hash_index', 'systems', ['inventory_id'], unique=False, postgresql_using='hash')
    op.create_index(op.f('ix_systems_operating_system'), 'systems', ['operating_system'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_systems_operating_system'), table_name='systems')
    op.drop_index('inventory_id_hash_index', table_name='systems', postgresql_using='hash')
    op.drop_index(op.f('ix_recommendation_rating_system_id'), table_name='recommendation_rating')
    op.drop_index(op.f('ix_recommendation_rating_rated_by'), table_name='recommendation_rating')
    op.drop_index(op.f('ix_performance_profile_history_report_date'), table_name='performance_profile_history')
    op.drop_index('non_optimized_system_profiles', table_name='performance_profile', postgresql_where=sa.text('number_of_recommendations > 0'))
    op.drop_index(op.f('ix_performance_profile_state'), table_name='performance_profile')
    # ### end Alembic commands ###