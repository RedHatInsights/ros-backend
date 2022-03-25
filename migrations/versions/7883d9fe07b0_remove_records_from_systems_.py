"""remove_records_from_systems

Revision ID: 7883d9fe07b0
Revises: 23d9d980a813
Create Date: 2022-03-16 13:01:01.665634

"""
from alembic import op
from ros.lib.models import (
    PerformanceProfile, System, db)
from ros.lib.utils import (
    get_or_create)

# revision identifiers, used by Alembic.
revision = '7883d9fe07b0'
down_revision = '23d9d980a813'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('UPDATE systems SET rule_hit_details=NULL, number_of_recommendations=NULL')
    op.drop_constraint('performance_profile_pkey','performance_profile')
    op.execute('ALTER TABLE performance_profile ADD CONSTRAINT "performance_profile_pkey" PRIMARY KEY (system_id)')


def downgrade():
    records = db.session.query(System, PerformanceProfile).join(PerformanceProfile, System.id == PerformanceProfile.system_id)

    for record in records:
        get_or_create(
                    db.session, System, ['id'],
                    id=record.System.id,
                    rule_hit_details=record.PerformanceProfile.rule_hit_details,
                    number_of_recommendations=record.PerformanceProfile.number_of_recommendations
        )
    db.session.commit()
    op.drop_constraint('performance_profile_pkey','performance_profile')
    op.execute('ALTER TABLE performance_profile ADD CONSTRAINT "performance_profile_pkey" PRIMARY KEY (system_id, report_date)')
    
    