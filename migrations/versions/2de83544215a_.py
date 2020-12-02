"""empty message

Revision ID: 2de83544215a
Revises: 
Create Date: 2020-12-02 15:54:10.628320

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2de83544215a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('performance_profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('host_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('avg_memory_used', sa.String(length=25), nullable=True),
    sa.Column('avg_memory', sa.String(length=25), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('performance_profile')
    # ### end Alembic commands ###