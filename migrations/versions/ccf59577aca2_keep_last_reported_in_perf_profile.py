"""keep last reported in perf profile

Revision ID: ccf59577aca2
Revises: 457844090fad
Create Date: 2022-03-24 21:02:10.471949

"""
from migrations.session_helpers import session
from sqlalchemy import func, tuple_, DateTime, Integer, Column
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision = 'ccf59577aca2'
down_revision = '457844090fad'
branch_labels = None
depends_on = None

Base = declarative_base()


class PerformanceProfile(Base):
    __tablename__ = "performance_profile"
    system_id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, primary_key=True)


def upgrade():
    with session() as session_obj:
        last_reported = (
            session_obj.query(
                PerformanceProfile.system_id,
                func.max(PerformanceProfile.report_date).label('max_date')
            ).group_by(PerformanceProfile.system_id).all()
        )
        if last_reported:
            rows_deleted = (
                session_obj.query(PerformanceProfile)
                .filter(
                    tuple_(
                        PerformanceProfile.system_id,
                        PerformanceProfile.report_date
                    ).notin_(last_reported)
                ).delete(synchronize_session='fetch')
            )
            print(
                f'Rows deleted from PerformanceProfile table={rows_deleted}'
            )


def downgrade():
    pass
