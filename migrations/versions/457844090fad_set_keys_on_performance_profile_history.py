"""set keys on performance profile history

Revision ID: 457844090fad
Revises: 8c6f4554d24d
Create Date: 2022-03-24 16:34:39.897983

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '457844090fad'
down_revision = '8c6f4554d24d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_primary_key(
        "pk_performance_profile_history", "performance_profile_history",
        ["system_id", "report_date"]
    )

    op.create_foreign_key(
        'fk_performance_profile_history_systems',
        'performance_profile_history', 'systems',
        ['system_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint(
        'pk_performance_profile_history',
        'performance_profile_history', type_='primary')
    op.drop_constraint(
        'fk_performance_profile_history_systems',
        'performance_profile_history', type_='foreignkey')
