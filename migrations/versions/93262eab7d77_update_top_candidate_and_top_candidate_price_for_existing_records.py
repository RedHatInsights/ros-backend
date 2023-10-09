"""Update top_candidate and top_candidate_price for existing records of PerformanceProfile

Revision ID: 93262eab7d77
Revises: c6f2cd708cea
Create Date: 2023-07-31 19:41:07.252297

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '93262eab7d77'
down_revision = 'c6f2cd708cea'
branch_labels = None
depends_on = None


def upgrade():
    try:
        print('Updating top_candidate and top_candidate_price for existing PerformanceProfile records!')
        op.execute(
            "update performance_profile set top_candidate = subquery.top_candidate, top_candidate_price = cast("
            "subquery.top_candidate_price as double precision) from (select rule_hit_details #> '{0,details,"
            "candidates,0,0}' as top_candidate, rule_hit_details #> '{0,details,candidates,0,"
            "1}' as top_candidate_price, system_id from performance_profile) as subquery where "
            "performance_profile.system_id = subquery.system_id")
    except sa.exc.SQLAlchemyError as err:
        print(f"Failed to update table with error {err}!")
    else:
        print('Successfully updated top_candidate and top_candidate_price for existing PerformanceProfile records!')
