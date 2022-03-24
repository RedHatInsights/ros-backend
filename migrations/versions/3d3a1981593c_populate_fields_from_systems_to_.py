"""populate fields from systems to performance profile

Revision ID: 3d3a1981593c
Revises: 015d7d1fea52
Create Date: 2022-03-23 23:45:14.430980

"""
from migrations.session_helpers import session
from sqlalchemy import func, DateTime, Integer, String, Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from ros.lib.utils import get_or_create

# revision identifiers, used by Alembic.
revision = '3d3a1981593c'
down_revision = '015d7d1fea52'
branch_labels = None
depends_on = None

Base = declarative_base()


class PerformanceProfile(Base):
    __tablename__ = "performance_profile"
    system_id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, primary_key=True)
    rule_hit_details = Column(JSONB)
    state = Column(String(25))
    number_of_recommendations = Column(Integer)
    operating_system = Column(JSONB)


class System(Base):
    __tablename__ = 'systems'
    id = Column(Integer, primary_key=True)
    inventory_id = Column(UUID(as_uuid=True), nullable=False)
    rule_hit_details = Column(JSONB)
    state = Column(String(25))
    number_of_recommendations = Column(Integer)
    operating_system = Column(JSONB)


def populate_fields_data_to_performance_profile():
    with session() as session_obj:
        last_reported = (
            session_obj.query(
                PerformanceProfile.system_id,
                func.max(PerformanceProfile.report_date).label('max_date')
            ).group_by(PerformanceProfile.system_id).subquery()
        )

        query = (
            session_obj.query(PerformanceProfile, System)
            .join(
                last_reported, (
                    last_reported.c.max_date == PerformanceProfile.report_date
                ) & (
                    PerformanceProfile.system_id == last_reported.c.system_id))
            .join(System, System.id == last_reported.c.system_id)
        )

        pp_results = query.all()
        for record in pp_results:
            try:
                get_or_create(
                    session_obj, PerformanceProfile,
                    ['system_id', 'report_date'],
                    system_id=record.System.id,
                    report_date=record.PerformanceProfile.report_date,
                    operating_system=record.System.operating_system,
                    state=record.System.state,
                    rule_hit_details=record.System.rule_hit_details,
                    number_of_recommendations=record.System.number_of_recommendations
                )
            except Exception as err:
                print(
                    'Failed to update performance_profile with '
                    f'system_id={record.System.id} and error={err}'
                )
                raise


def upgrade():
    populate_fields_data_to_performance_profile()


def downgrade():
    pass
