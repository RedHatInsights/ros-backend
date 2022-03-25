"""delete_existing_historical_records_from_PP

Revision ID: 23d9d980a813
Revises: 29bd24943ac5
Create Date: 2022-03-17 18:23:31.141150

"""
from sqlalchemy import tuple_
from ros.lib.models import (
    PerformanceProfile, PerformanceProfileHistory, System, RhAccount, db)
from ros.lib.utils import (system_ids_by_account, get_or_create)
from sqlalchemy import func
from alembic import op


# revision identifiers, used by Alembic.
revision = '23d9d980a813'
down_revision = '29bd24943ac5'
branch_labels = None
depends_on = None

records = db.session.query(System, PerformanceProfile, PerformanceProfileHistory).join(PerformanceProfile, System.id == PerformanceProfile.system_id).join(PerformanceProfileHistory, PerformanceProfileHistory.system_id == System.id)
account_list = db.session.query(RhAccount.account).all()


def upgrade():
    for account in account_list:
        if account:
            system_query = system_ids_by_account(account).subquery()
            last_reported = db.session.query(PerformanceProfile.system_id, func.max(PerformanceProfile.report_date) \
                .label('last_date')).filter(PerformanceProfile.system_id.in_(system_query)).group_by(PerformanceProfile.system_id).all()

            if last_reported:
                delete_records = db.session.query(PerformanceProfile).filter(PerformanceProfile.system_id.in_(system_query)) \
                    .filter(tuple_(PerformanceProfile.system_id, PerformanceProfile.report_date).notin_(last_reported))

                if delete_records.all():
                    delete_records.delete(synchronize_session=False)
                    db.session.commit()

    for record in records:
        get_or_create(
                    db.session, PerformanceProfile, ['system_id', 'report_date'],
                    system_id=record.System.id,
                    operating_system=record.System.operating_system,
                    state=record.System.state,
                    report_date=record.PerformanceProfile.report_date,
                    rule_hit_details=record.PerformanceProfileHistory.rule_hit_details,
                    number_of_recommendations=record.PerformanceProfileHistory.number_of_recommendations
        )
    db.session.commit()

def downgrade():
    for account in account_list:
        if account:
            system_query = system_ids_by_account(account).subquery()
            last_reported = db.session.query(PerformanceProfile.system_id, func.max(PerformanceProfile.report_date) \
                .label('last_date')).filter(PerformanceProfile.system_id.in_(system_query)).group_by(PerformanceProfile.system_id).all()
            
            if last_reported:
                    add_records = db.session.query(PerformanceProfileHistory).filter(PerformanceProfileHistory.system_id.in_(system_query)).filter(tuple_(PerformanceProfileHistory.system_id, PerformanceProfileHistory.report_date).notin_(last_reported))

                    for record in add_records:
                        get_or_create(
                            db.session, PerformanceProfile, ['system_id', 'report_date'],
                            system_id=record.system_id,
                            performance_record=record.performance_record,
                            performance_utilization=record.performance_utilization,
                            report_date=record.report_date
                        )
                    db.session.commit()
    op.execute('UPDATE performance_profile SET state=NULL, operating_system=NULL, rule_hit_details=NULL, number_of_recommendations=NULL')

