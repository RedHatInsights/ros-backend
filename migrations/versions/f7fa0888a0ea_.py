"""empty message

Revision ID: f7fa0888a0ea
Revises: 37ef515b370d
Create Date: 2021-02-17 13:52:48.369837

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7fa0888a0ea'
down_revision = '37ef515b370d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rh_accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account', sa.Text(), nullable=False),
    sa.UniqueConstraint('account'),
    sa.CheckConstraint('NOT(account IS NULL)'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('systems',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('inventory_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['rh_accounts.id'], name='systems_account_id_fkey'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('inventory_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('systems')
    op.drop_table('rh_accounts')
    # ### end Alembic commands ###
