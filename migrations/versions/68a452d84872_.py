"""empty message

Revision ID: 68a452d84872
Revises: 1346a9f01aa8
Create Date: 2019-02-04 11:57:49.225142

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '68a452d84872'
down_revision = '1346a9f01aa8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('dataset', 'version_number',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('dataset', 'version_number',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###