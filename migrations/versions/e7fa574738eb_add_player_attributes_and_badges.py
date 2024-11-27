"""Add player attributes and badges

Revision ID: e7fa574738eb
Revises: 
Create Date: 2024-09-10 08:19:23.460547

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7fa574738eb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('player', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acceleration', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('agility', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ball_handle', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('block', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('defensive_consistency', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('defensive_rebound', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('draw_foul', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('driving_dunk', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('free_throw', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hands', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('help_defense_iq', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hustle', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('intangibles', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('interior_defense', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('lateral_quickness', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('layup', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('mid_range_shot', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('offensive_consistency', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('offensive_rebound', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('overall_durability', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pass_accuracy', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pass_iq', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pass_perception', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pass_vision', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('perimeter_defense', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('post_control', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('post_fade', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('post_hook', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('shot_iq', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('standing_dunk', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('speed', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('speed_with_ball', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('stamina', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('steal', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('strength', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('three_point_shot', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('vertical', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('aerial_wizard', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('ankle_assassin', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('bail_out', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('boxout_beast', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('break_starter', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('brick_wall', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('challenger', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('deadeye', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('dimer', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('float_game', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('glove', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('handles_for_days', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('high_flying_denier', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('hook_specialist', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('immovable_enforcer', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('interceptor', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('layup_mixmaster', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('lightning_launch', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('limitless_range', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('mini_marksman', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('off_ball_pest', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('on_ball_menace', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('paint_patroller', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('paint_prodigy', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('pick_dodger', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('pogo_stick', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('posterizer', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('post_fade_phenom', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('post_lockdown', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('post_powerhouse', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('post_up_poet', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('physical_finisher', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('rebound_chaser', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('set_shot_specialist', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('shifty_shooter', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('slippery_off_ball', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('strong_handle', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('unpluckable', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('versatile_visionary', sa.String(length=20), nullable=True))
        batch_op.drop_column('shooting')
        batch_op.drop_column('badges')
        batch_op.drop_column('defense')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('player', schema=None) as batch_op:
        batch_op.add_column(sa.Column('defense', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('badges', sa.VARCHAR(length=200), nullable=True))
        batch_op.add_column(sa.Column('shooting', sa.INTEGER(), nullable=True))
        batch_op.drop_column('versatile_visionary')
        batch_op.drop_column('unpluckable')
        batch_op.drop_column('strong_handle')
        batch_op.drop_column('slippery_off_ball')
        batch_op.drop_column('shifty_shooter')
        batch_op.drop_column('set_shot_specialist')
        batch_op.drop_column('rebound_chaser')
        batch_op.drop_column('physical_finisher')
        batch_op.drop_column('post_up_poet')
        batch_op.drop_column('post_powerhouse')
        batch_op.drop_column('post_lockdown')
        batch_op.drop_column('post_fade_phenom')
        batch_op.drop_column('posterizer')
        batch_op.drop_column('pogo_stick')
        batch_op.drop_column('pick_dodger')
        batch_op.drop_column('paint_prodigy')
        batch_op.drop_column('paint_patroller')
        batch_op.drop_column('on_ball_menace')
        batch_op.drop_column('off_ball_pest')
        batch_op.drop_column('mini_marksman')
        batch_op.drop_column('limitless_range')
        batch_op.drop_column('lightning_launch')
        batch_op.drop_column('layup_mixmaster')
        batch_op.drop_column('interceptor')
        batch_op.drop_column('immovable_enforcer')
        batch_op.drop_column('hook_specialist')
        batch_op.drop_column('high_flying_denier')
        batch_op.drop_column('handles_for_days')
        batch_op.drop_column('glove')
        batch_op.drop_column('float_game')
        batch_op.drop_column('dimer')
        batch_op.drop_column('deadeye')
        batch_op.drop_column('challenger')
        batch_op.drop_column('brick_wall')
        batch_op.drop_column('break_starter')
        batch_op.drop_column('boxout_beast')
        batch_op.drop_column('bail_out')
        batch_op.drop_column('ankle_assassin')
        batch_op.drop_column('aerial_wizard')
        batch_op.drop_column('vertical')
        batch_op.drop_column('three_point_shot')
        batch_op.drop_column('strength')
        batch_op.drop_column('steal')
        batch_op.drop_column('stamina')
        batch_op.drop_column('speed_with_ball')
        batch_op.drop_column('speed')
        batch_op.drop_column('standing_dunk')
        batch_op.drop_column('shot_iq')
        batch_op.drop_column('post_hook')
        batch_op.drop_column('post_fade')
        batch_op.drop_column('post_control')
        batch_op.drop_column('perimeter_defense')
        batch_op.drop_column('pass_vision')
        batch_op.drop_column('pass_perception')
        batch_op.drop_column('pass_iq')
        batch_op.drop_column('pass_accuracy')
        batch_op.drop_column('overall_durability')
        batch_op.drop_column('offensive_rebound')
        batch_op.drop_column('offensive_consistency')
        batch_op.drop_column('mid_range_shot')
        batch_op.drop_column('layup')
        batch_op.drop_column('lateral_quickness')
        batch_op.drop_column('interior_defense')
        batch_op.drop_column('intangibles')
        batch_op.drop_column('hustle')
        batch_op.drop_column('help_defense_iq')
        batch_op.drop_column('hands')
        batch_op.drop_column('free_throw')
        batch_op.drop_column('driving_dunk')
        batch_op.drop_column('draw_foul')
        batch_op.drop_column('defensive_rebound')
        batch_op.drop_column('defensive_consistency')
        batch_op.drop_column('block')
        batch_op.drop_column('ball_handle')
        batch_op.drop_column('agility')
        batch_op.drop_column('acceleration')

    # ### end Alembic commands ###
