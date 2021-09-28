"""modify keys in performance_utilization

Revision ID: de502e7c8c6a
Revises: 397d8c6c506a
Create Date: 2021-09-15 14:33:26.386292

"""
from sqlalchemy import Date, Integer, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base


from migrations.session_helpers import session

# revision identifiers, used by Alembic.
revision = 'de502e7c8c6a'
down_revision = '397d8c6c506a'
branch_labels = None
depends_on = None


Base = declarative_base()


class PerformanceProfile(Base):
    __tablename__ = "performance_profile"
    system_id = Column(Integer, primary_key=True)
    report_date = Column(Date, primary_key=True)
    performance_utilization = Column(JSONB)


def handle_score_substring(remove_score=True):
    with session() as s:
        profiles = s.query(PerformanceProfile).all()
        for row in profiles:
            try:
                utilization = {}
                for key, value in row.performance_utilization.items():
                    if remove_score:
                        utilization[key.replace('_score', '')] = value
                    else:
                        utilization[key + '_score'] = value
                    setattr(
                        row, 'performance_utilization', utilization
                    )
            except Exception as err:
                print(
                    "Update failed for record with id=%d and error=%s",
                    row.id, err)
                raise


def upgrade():
    handle_score_substring()


def downgrade():
    handle_score_substring(False)
