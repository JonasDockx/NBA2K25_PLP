"""
We will define the User and Player models here.
"""

from flask_login import UserMixin
from sqlalchemy.orm import validates

from app import db


class User(db.Model, UserMixin):
    """
    This is the user model that we will use.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    players = db.relationship("Player", back_populates="user", cascade="all, delete-orphan")
    settings = db.relationship(
        "UserSettings", 
        uselist=False, 
        back_populates="user",
        cascade="all, delete-orphan",
        )


class Player(db.Model):
    """
    This is the player model that we will use.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE", name="fk_user_player"), nullable=False)

    user = db.relationship("User", back_populates="players")
    targets = db.relationship("PlayerTargets", back_populates="player", uselist=False, cascade="all, delete-orphan")

    # Development and badge points
    devpoints = db.Column(db.Integer, default=0)
    badgepoints = db.Column(db.Integer, default=0)

    # Attributes (25 to 99)
    agility = db.Column(db.Integer, default=25)
    ball_handle = db.Column(db.Integer, default=25)
    block = db.Column(db.Integer, default=25)
    close_shot = db.Column(db.Integer, default=25)
    defensive_consistency = db.Column(db.Integer, default=25)
    defensive_rebound = db.Column(db.Integer, default=25)
    draw_foul = db.Column(db.Integer, default=25)
    driving_dunk = db.Column(db.Integer, default=25)
    free_throw = db.Column(db.Integer, default=25)
    hands = db.Column(db.Integer, default=25)
    help_defense_iq = db.Column(db.Integer, default=25)
    hustle = db.Column(db.Integer, default=25)
    intangibles = db.Column(db.Integer, default=25)
    interior_defense = db.Column(db.Integer, default=25)
    layup = db.Column(db.Integer, default=25)
    mid_range_shot = db.Column(db.Integer, default=25)
    offensive_consistency = db.Column(db.Integer, default=25)
    offensive_rebound = db.Column(db.Integer, default=25)
    overall_durability = db.Column(db.Integer, default=25)
    pass_accuracy = db.Column(db.Integer, default=25)
    pass_iq = db.Column(db.Integer, default=25)
    pass_perception = db.Column(db.Integer, default=25)
    pass_vision = db.Column(db.Integer, default=25)
    perimeter_defense = db.Column(db.Integer, default=25)
    post_control = db.Column(db.Integer, default=25)
    post_fade = db.Column(db.Integer, default=25)
    post_hook = db.Column(db.Integer, default=25)
    shot_iq = db.Column(db.Integer, default=25)
    standing_dunk = db.Column(db.Integer, default=25)
    speed = db.Column(db.Integer, default=25)
    speed_with_ball = db.Column(db.Integer, default=25)
    stamina = db.Column(db.Integer, default=25)
    steal = db.Column(db.Integer, default=25)
    strength = db.Column(db.Integer, default=25)
    three_point_shot = db.Column(db.Integer, default=25)
    vertical = db.Column(db.Integer, default=25)

    # Badges (None by default)
    aerial_wizard = db.Column(db.String(20), default="None")
    ankle_assassin = db.Column(db.String(20), default="None")
    bail_out = db.Column(db.String(20), default="None")
    boxout_beast = db.Column(db.String(20), default="None")
    break_starter = db.Column(db.String(20), default="None")
    brick_wall = db.Column(db.String(20), default="None")
    challenger = db.Column(db.String(20), default="None")
    deadeye = db.Column(db.String(20), default="None")
    dimer = db.Column(db.String(20), default="None")
    float_game = db.Column(db.String(20), default="None")
    glove = db.Column(db.String(20), default="None")
    handles_for_days = db.Column(db.String(20), default="None")
    high_flying_denier = db.Column(db.String(20), default="None")
    hook_specialist = db.Column(db.String(20), default="None")
    immovable_enforcer = db.Column(db.String(20), default="None")
    interceptor = db.Column(db.String(20), default="None")
    layup_mixmaster = db.Column(db.String(20), default="None")
    lightning_launch = db.Column(db.String(20), default="None")
    limitless_range = db.Column(db.String(20), default="None")
    mini_marksman = db.Column(db.String(20), default="None")
    off_ball_pest = db.Column(db.String(20), default="None")
    on_ball_menace = db.Column(db.String(20), default="None")
    paint_patroller = db.Column(db.String(20), default="None")
    paint_prodigy = db.Column(db.String(20), default="None")
    pick_dodger = db.Column(db.String(20), default="None")
    pogo_stick = db.Column(db.String(20), default="None")
    posterizer = db.Column(db.String(20), default="None")
    post_fade_phenom = db.Column(db.String(20), default="None")
    post_lockdown = db.Column(db.String(20), default="None")
    post_powerhouse = db.Column(db.String(20), default="None")
    post_up_poet = db.Column(db.String(20), default="None")
    physical_finisher = db.Column(db.String(20), default="None")
    rebound_chaser = db.Column(db.String(20), default="None")
    rise_up = db.Column(db.String(20), default="None")
    set_shot_specialist = db.Column(db.String(20), default="None")
    shifty_shooter = db.Column(db.String(20), default="None")
    slippery_off_ball = db.Column(db.String(20), default="None")
    strong_handle = db.Column(db.String(20), default="None")
    unpluckable = db.Column(db.String(20), default="None")
    versatile_visionary = db.Column(db.String(20), default="None")

    @validates("agility", "ball_handle", "block", "close_shot", "defensive_consistency", "defensive_rebound", "draw_foul", "driving_dunk", "free_throw", "hands", "help_defense_iq", "hustle", "intangibles", "interior_defense", "layup", "mid_range_shot", "offensive_consistency", "offensive_rebound", "overall_durability", "pass_accuracy", "pass_iq", "pass_perception", "pass_vision", "perimeter_defense", "post_control", "post_fade", "post_hook", "shot_iq", "standing_dunk", "speed", "speed_with_ball", "stamina", "steal", "strength", "three_point_shot", "vertical")
    def validate_attributes(self, key, value):
        """
        Validating attributes to see if values are between 25 and 99.
        """
        if value < 25 or value > 99:
            raise ValueError(f"{key} must be between 25 and 99.")
        return value

class UserSettings(db.Model):
    """
    Defining the user settings.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
        )

    # Customizable point and badge values
    rebounds_points_10 = db.Column(db.Integer, default=1)
    assists_points_10 = db.Column(db.Integer, default=1)
    points_70 = db.Column(db.Integer, default=20)
    points_60 = db.Column(db.Integer, default=15)
    points_50 = db.Column(db.Integer, default=10)
    points_40 = db.Column(db.Integer, default=5)
    points_30 = db.Column(db.Integer, default=3)
    points_20 = db.Column(db.Integer, default=2)
    points_10 = db.Column(db.Integer, default=1)

    rebounds_20 = db.Column(db.Integer, default=3)  # Ensure this field exists
    rebounds_10 = db.Column(db.Integer, default=1)

    assists_20 = db.Column(db.Integer, default=3)
    assists_10 = db.Column(db.Integer, default=1)

    double_double_2 = db.Column(db.Integer, default=3)
    double_double_3 = db.Column(db.Integer, default=5)
    double_double_4 = db.Column(db.Integer, default=15)
    double_double_5 = db.Column(db.Integer, default=30)

    steals_10 = db.Column(db.Integer, default=5)
    steals_6 = db.Column(db.Integer, default=3)
    steals_3 = db.Column(db.Integer, default=1)

    blocks_10 = db.Column(db.Integer, default=5)
    blocks_6 = db.Column(db.Integer, default=3)
    blocks_3 = db.Column(db.Integer, default=1)

    player_of_the_game = db.Column(db.Integer, default=1)
    player_of_the_week = db.Column(db.Integer, default=3)
    player_of_the_month = db.Column(db.Integer, default=5)

    roty_points = db.Column(db.Integer, default=7)
    roty_badge = db.Column(db.Integer, default=3)
    dpoy_points = db.Column(db.Integer, default=5)
    dpoy_badge = db.Column(db.Integer, default=3)
    mvp_points = db.Column(db.Integer, default=15)
    mvp_badge = db.Column(db.Integer, default=3)
    champion_points = db.Column(db.Integer, default=10)
    champion_badge = db.Column(db.Integer, default=2)

    user = db.relationship("User", back_populates="settings")

class PlayerTargets(db.Model):
    """
    This is a model for setting target values for players when it comes to attributes and badges.
    """
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id", ondelete="CASCADE"), nullable=False)

    agility = db.Column(db.Integer, default=25)
    ball_handle = db.Column(db.Integer, default=25)
    block = db.Column(db.Integer, default=25)
    close_shot = db.Column(db.Integer, default=25)
    defensive_consistency = db.Column(db.Integer, default=25)
    defensive_rebound = db.Column(db.Integer, default=25)
    draw_foul = db.Column(db.Integer, default=25)
    driving_dunk = db.Column(db.Integer, default=25)
    free_throw = db.Column(db.Integer, default=25)
    hands = db.Column(db.Integer, default=25)
    help_defense_iq = db.Column(db.Integer, default=25)
    hustle = db.Column(db.Integer, default=25)
    intangibles = db.Column(db.Integer, default=25)
    interior_defense = db.Column(db.Integer, default=25)
    layup = db.Column(db.Integer, default=25)
    mid_range_shot = db.Column(db.Integer, default=25)
    offensive_consistency = db.Column(db.Integer, default=25)
    offensive_rebound = db.Column(db.Integer, default=25)
    overall_durability = db.Column(db.Integer, default=25)
    pass_accuracy = db.Column(db.Integer, default=25)
    pass_iq = db.Column(db.Integer, default=25)
    pass_perception = db.Column(db.Integer, default=25)
    pass_vision = db.Column(db.Integer, default=25)
    perimeter_defense = db.Column(db.Integer, default=25)
    post_control = db.Column(db.Integer, default=25)
    post_fade = db.Column(db.Integer, default=25)
    post_hook = db.Column(db.Integer, default=25)
    shot_iq = db.Column(db.Integer, default=25)
    standing_dunk = db.Column(db.Integer, default=25)
    speed = db.Column(db.Integer, default=25)
    speed_with_ball = db.Column(db.Integer, default=25)
    stamina = db.Column(db.Integer, default=25)
    steal = db.Column(db.Integer, default=25)
    strength = db.Column(db.Integer, default=25)
    three_point_shot = db.Column(db.Integer, default=25)
    vertical = db.Column(db.Integer, default=25)

    # Badges (None by default)
    aerial_wizard = db.Column(db.String(20), default="None")
    ankle_assassin = db.Column(db.String(20), default="None")
    bail_out = db.Column(db.String(20), default="None")
    boxout_beast = db.Column(db.String(20), default="None")
    break_starter = db.Column(db.String(20), default="None")
    brick_wall = db.Column(db.String(20), default="None")
    challenger = db.Column(db.String(20), default="None")
    deadeye = db.Column(db.String(20), default="None")
    dimer = db.Column(db.String(20), default="None")
    float_game = db.Column(db.String(20), default="None")
    glove = db.Column(db.String(20), default="None")
    handles_for_days = db.Column(db.String(20), default="None")
    high_flying_denier = db.Column(db.String(20), default="None")
    hook_specialist = db.Column(db.String(20), default="None")
    immovable_enforcer = db.Column(db.String(20), default="None")
    interceptor = db.Column(db.String(20), default="None")
    layup_mixmaster = db.Column(db.String(20), default="None")
    lightning_launch = db.Column(db.String(20), default="None")
    limitless_range = db.Column(db.String(20), default="None")
    mini_marksman = db.Column(db.String(20), default="None")
    off_ball_pest = db.Column(db.String(20), default="None")
    on_ball_menace = db.Column(db.String(20), default="None")
    paint_patroller = db.Column(db.String(20), default="None")
    paint_prodigy = db.Column(db.String(20), default="None")
    pick_dodger = db.Column(db.String(20), default="None")
    pogo_stick = db.Column(db.String(20), default="None")
    posterizer = db.Column(db.String(20), default="None")
    post_fade_phenom = db.Column(db.String(20), default="None")
    post_lockdown = db.Column(db.String(20), default="None")
    post_powerhouse = db.Column(db.String(20), default="None")
    post_up_poet = db.Column(db.String(20), default="None")
    physical_finisher = db.Column(db.String(20), default="None")
    rebound_chaser = db.Column(db.String(20), default="None")
    rise_up = db.Column(db.String(20), default="None")
    set_shot_specialist = db.Column(db.String(20), default="None")
    shifty_shooter = db.Column(db.String(20), default="None")
    slippery_off_ball = db.Column(db.String(20), default="None")
    strong_handle = db.Column(db.String(20), default="None")
    unpluckable = db.Column(db.String(20), default="None")
    versatile_visionary = db.Column(db.String(20), default="None")

    player = db.relationship("Player", back_populates="targets")
