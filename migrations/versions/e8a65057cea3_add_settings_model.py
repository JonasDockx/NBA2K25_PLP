"""Add settings model

Revision ID: e8a65057cea3
Revises: cc642208f245
Create Date: 2024-09-18 11:30:07.809667

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8a65057cea3'
down_revision = 'cc642208f245'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('rebounds_points_10', sa.Integer(), nullable=True),
    sa.Column('assists_points_10', sa.Integer(), nullable=True),
    sa.Column('points_70', sa.Integer(), nullable=True),
    sa.Column('points_60', sa.Integer(), nullable=True),
    sa.Column('points_50', sa.Integer(), nullable=True),
    sa.Column('points_40', sa.Integer(), nullable=True),
    sa.Column('points_30', sa.Integer(), nullable=True),
    sa.Column('points_20', sa.Integer(), nullable=True),
    sa.Column('double_double_2', sa.Integer(), nullable=True),
    sa.Column('double_double_3', sa.Integer(), nullable=True),
    sa.Column('double_double_4', sa.Integer(), nullable=True),
    sa.Column('double_double_5', sa.Integer(), nullable=True),
    sa.Column('steals_10', sa.Integer(), nullable=True),
    sa.Column('steals_6', sa.Integer(), nullable=True),
    sa.Column('steals_3', sa.Integer(), nullable=True),
    sa.Column('blocks_10', sa.Integer(), nullable=True),
    sa.Column('blocks_6', sa.Integer(), nullable=True),
    sa.Column('blocks_3', sa.Integer(), nullable=True),
    sa.Column('player_of_the_game', sa.Integer(), nullable=True),
    sa.Column('player_of_the_week', sa.Integer(), nullable=True),
    sa.Column('player_of_the_month', sa.Integer(), nullable=True),
    sa.Column('roty_points', sa.Integer(), nullable=True),
    sa.Column('roty_badge', sa.Integer(), nullable=True),
    sa.Column('dpoy_points', sa.Integer(), nullable=True),
    sa.Column('dpoy_badge', sa.Integer(), nullable=True),
    sa.Column('mvp_points', sa.Integer(), nullable=True),
    sa.Column('mvp_badge', sa.Integer(), nullable=True),
    sa.Column('champion_points', sa.Integer(), nullable=True),
    sa.Column('champion_badge', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_settings')
    # ### end Alembic commands ###