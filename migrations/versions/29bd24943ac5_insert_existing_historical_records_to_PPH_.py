"""insert_existing_historical_records_to_PPH

Revision ID: 29bd24943ac5
Revises: ada4f233b40c
Create Date: 2022-03-17 14:45:29.383448

"""
from ros.lib.models import (
    PerformanceProfile, PerformanceProfileHistory, System, db)
from ros.lib.utils import (
    get_or_create)
from alembic import op


# revision identifiers, used by Alembic.
revision = '29bd24943ac5'
down_revision = '9f16ec63696b'
branch_labels = None
depends_on = None

records = db.session.query(PerformanceProfile, System).join(System, System.id == PerformanceProfile.system_id)

def upgrade():
    for record in records:
        get_or_create(
                    db.session, PerformanceProfileHistory, ['system_id', 'report_date'],
                    system_id=record.PerformanceProfile.system_id,
                    performance_record=record.PerformanceProfile.performance_record,
                    performance_utilization=record.PerformanceProfile.performance_utilization,
                    report_date=record.PerformanceProfile.report_date,
                    operating_system=record.System.operating_system,
                    state=record.System.state,
                    rule_hit_details=record.System.rule_hit_details,
                    number_of_recommendations=record.System.number_of_recommendations
        )
    db.session.commit()


def downgrade():
    op.execute("Delete from performance_profile_history")
        

