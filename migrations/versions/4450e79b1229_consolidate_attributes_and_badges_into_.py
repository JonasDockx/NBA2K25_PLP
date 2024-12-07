"""Consolidate attributes and badges into Player model

Revision ID: 4450e79b1229
Revises: e7fa574738eb
Create Date: 2024-09-10 13:03:31.728642

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4450e79b1229'
down_revision = 'e7fa574738eb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('player', schema=None) as batch_op:
        batch_op.add_column(sa.Column('devpoints', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('badgepoints', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('player', schema=None) as batch_op:
        batch_op.drop_column('badgepoints')
        batch_op.drop_column('devpoints')

    # ### end Alembic commands ###
