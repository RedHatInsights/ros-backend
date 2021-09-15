"""modify keys in performance_utilization

Revision ID: de502e7c8c6a
Revises: 397d8c6c506a
Create Date: 2021-09-15 14:33:26.386292

"""
from alembic import op
import sqlalchemy as sa
from ros.lib.models import db, PerformanceProfile


# revision identifiers, used by Alembic.
revision = 'de502e7c8c6a'
down_revision = '397d8c6c506a'
branch_labels = None
depends_on = None


def handle_score_substring(remove_score=True):
    profiles = db.session.query(PerformanceProfile).all()
    for row in profiles:
        try:
            performance_utilization = {}
            for key, value in row.performance_utilization.items():
                if remove_score:
                    performance_utilization[key.replace('_score', '')] = value
                else:
                    performance_utilization[key + '_score'] = value
                setattr(
                    row, 'performance_utilization', performance_utilization
                )
        except Exception as err:
            print(
                "Update failed for record with id=%d and error=%s",
                row.id, err)
    db.session.commit()


def upgrade():
    handle_score_substring()


def downgrade():
    handle_score_substring(False)
