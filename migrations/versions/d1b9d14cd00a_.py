"""empty message

Revision ID: d1b9d14cd00a
Revises: 7805dfde3ca9
Create Date: 2021-03-16 14:35:55.627096

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1b9d14cd00a'
down_revision = '7805dfde3ca9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('systems', 'state')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('systems', sa.Column('state', sa.VARCHAR(length=25), autoincrement=False, nullable=True))
    # ### end Alembic commands ###