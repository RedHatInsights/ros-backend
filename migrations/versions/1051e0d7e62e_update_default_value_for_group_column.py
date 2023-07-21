"""update default value for group column

Revision ID: 1051e0d7e62e
Revises: b21a2ec1a281
Create Date: 2023-07-21 20:50:08.705356

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1051e0d7e62e'
down_revision = 'b21a2ec1a281'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('systems', 'groups', server_default=sa.text("'[]'"))


def downgrade():
    pass
