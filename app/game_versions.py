"""
What exists in each Game Version.

A Game Version is the edition of NBA 2K a Player is tracked in ("2K25", "2K26"
or "2K27"). It decides which Badges and Attributes exist for that Player. It
does not affect the points economy: upgrade costs are shared by every version.

This module is plain Python on purpose - no database, no Flask - so it can be
imported and tested on its own. It is the single place to edit when a new game
comes out.
"""

# --- Badge levels ------------------------------------------------------------

# In order, worst to best. "None" is the string, not Python's None: that is how
# the level is stored today and how the templates compare it.
BADGE_LEVELS = ["None", "Bronze", "Silver", "Gold", "Hall of Fame", "Legendary"]

DEFAULT_BADGE_LEVEL = "None"
DEFAULT_TARGET_BADGE_LEVEL = "Legendary"

# --- Upgrade costs -----------------------------------------------------------

# Devpoints to raise a badge one level, keyed by the level it is at now.
# "Legendary" is absent: it is the top, so it cannot be upgraded.
BADGE_UPGRADE_COSTS = {
    "None": 3,
    "Bronze": 5,
    "Silver": 7,
    "Gold": 10,
    "Hall of Fame": 20,
}

# Devpoints to raise an attribute by one point, as (below_this_value, cost).
# The first row whose threshold the current value is under wins.
ATTRIBUTE_UPGRADE_COSTS = [(70, 1), (80, 2), (90, 3)]
ATTRIBUTE_UPGRADE_COST_ABOVE = 5

MIN_ATTRIBUTE_VALUE = 25
MAX_ATTRIBUTE_VALUE = 99
DEFAULT_TARGET_ATTRIBUTE_VALUE = 99


def badge_upgrade_cost(level):
    """Devpoints to move a badge up from `level`, or None if it cannot move."""
    return BADGE_UPGRADE_COSTS.get(level)


def next_badge_level(level):
    """The level above `level`, or None if it is already Legendary/unknown."""
    if level not in BADGE_LEVELS:
        return None
    index = BADGE_LEVELS.index(level)
    if index + 1 >= len(BADGE_LEVELS):
        return None
    return BADGE_LEVELS[index + 1]


def attribute_upgrade_cost(value):
    """Devpoints to raise an attribute from `value` to `value` + 1."""
    for threshold, cost in ATTRIBUTE_UPGRADE_COSTS:
        if value < threshold:
            return cost
    return ATTRIBUTE_UPGRADE_COST_ABOVE


# --- Attributes --------------------------------------------------------------

# Identical in all three Game Versions. Display names are stored rather than
# guessed with .title(), which gets "Three Point Shot" and "Pass Iq" wrong.
ATTRIBUTE_NAMES = {
    "agility": "Agility",
    "ball_handle": "Ball Handle",
    "block": "Block",
    "close_shot": "Close Shot",
    "defensive_consistency": "Defensive Consistency",
    "defensive_rebound": "Defensive Rebound",
    "draw_foul": "Draw Foul",
    "driving_dunk": "Driving Dunk",
    "free_throw": "Free Throw",
    "hands": "Hands",
    "help_defense_iq": "Help Defense IQ",
    "hustle": "Hustle",
    "intangibles": "Intangibles",
    "interior_defense": "Interior Defense",
    "layup": "Layup",
    "mid_range_shot": "Mid-Range Shot",
    "offensive_consistency": "Offensive Consistency",
    "offensive_rebound": "Offensive Rebound",
    "overall_durability": "Overall Durability",
    "pass_accuracy": "Pass Accuracy",
    "pass_iq": "Pass IQ",
    "pass_perception": "Pass Perception",
    "pass_vision": "Pass Vision",
    "perimeter_defense": "Perimeter Defense",
    "post_control": "Post Control",
    "post_fade": "Post Fade",
    "post_hook": "Post Hook",
    "shot_iq": "Shot IQ",
    "speed": "Speed",
    "speed_with_ball": "Speed with Ball",
    "stamina": "Stamina",
    "standing_dunk": "Standing Dunk",
    "steal": "Steal",
    "strength": "Strength",
    "three_point_shot": "Three-Point Shot",
    "vertical": "Vertical",
}

_ATTRIBUTES = sorted(ATTRIBUTE_NAMES)

# --- Badges ------------------------------------------------------------------

# Every badge key that exists in any version, with its proper display name.
# Which version a badge belongs to is decided by the lists further down, not by
# this dictionary.
BADGE_NAMES = {
    "aerial_wizard": "Aerial Wizard",
    "ankle_assassin": "Ankle Assassin",
    "ankle_braces": "Ankle Braces",
    "arc_cadence": "Arc Cadence",
    "bail_out": "Bail Out",
    "boxout_beast": "Boxout Beast",
    "boxout_boss": "Boxout Boss",
    "break_starter": "Break Starter",
    "breaker": "Breaker",
    "brick_wall": "Brick Wall",
    "bruiser": "Bruiser",
    "challenger": "Challenger",
    "crasher": "Crasher",
    "deadeye": "Deadeye",
    "dimer": "Dimer",
    "flash": "Flash",
    "float_game": "Float Game",
    "ghost_stepper": "Ghost Stepper",
    "glove": "Glove",
    "handles_for_days": "Handles for Days",
    "high_flying_denier": "High-Flying Denier",
    "hook_specialist": "Hook Specialist",
    "immovable_enforcer": "Immovable Enforcer",
    "interceptor": "Interceptor",
    "layup_mixmaster": "Layup Mixmaster",
    "lightning_launch": "Lightning Launch",
    "limitless_range": "Limitless Range",
    "mini_marksman": "Mini Marksman",
    "off_ball_pest": "Off-Ball Pest",
    "on_ball_menace": "On-Ball Menace",
    "pace": "Pace",
    "paint_patroller": "Paint Patroller",
    "paint_prodigy": "Paint Prodigy",
    "physical_finisher": "Physical Finisher",
    "pick_dodger": "Pick Dodger",
    "pogo_stick": "Pogo Stick",
    "possession_closer": "Possession Closer",
    "post_fade_phenom": "Post Fade Phenom",
    "post_lockdown": "Post Lockdown",
    "post_powerhouse": "Post Powerhouse",
    "post_spin_catalyst": "Post Spin Catalyst",
    "post_up_poet": "Post Up Poet",
    "posterizer": "Posterizer",
    "quick_trigger": "Quick Trigger",
    "rebound_chaser": "Rebound Chaser",
    "rise_up": "Rise Up",
    "seatbelt": "Seatbelt",
    "set_and_fire": "Set and Fire",
    "set_shot_specialist": "Set Shot Specialist",
    "shifty_shooter": "Shifty Shooter",
    "slippery_off_ball": "Slippery Off-Ball",
    "smooth_operator": "Smooth Operator",
    "static_middy": "Static Middy",
    "strong_handle": "Strong Handle",
    "sync_snatcher": "Sync Snatcher",
    "unpluckable": "Unpluckable",
    "versatile_visionary": "Versatile Visionary",
    "wall_up": "Wall Up",
    "work_horse": "Work Horse",
}

# The 40 badges of NBA 2K25. NBA 2K26 shipped the same set, so it points at this
# same list rather than repeating it.
_BADGES_2K25 = sorted([
    "aerial_wizard",
    "ankle_assassin",
    "bail_out",
    "boxout_beast",
    "break_starter",
    "brick_wall",
    "challenger",
    "deadeye",
    "dimer",
    "float_game",
    "glove",
    "handles_for_days",
    "high_flying_denier",
    "hook_specialist",
    "immovable_enforcer",
    "interceptor",
    "layup_mixmaster",
    "lightning_launch",
    "limitless_range",
    "mini_marksman",
    "off_ball_pest",
    "on_ball_menace",
    "paint_patroller",
    "paint_prodigy",
    "physical_finisher",
    "pick_dodger",
    "pogo_stick",
    "post_fade_phenom",
    "post_lockdown",
    "post_powerhouse",
    "post_up_poet",
    "posterizer",
    "rebound_chaser",
    "rise_up",
    "set_shot_specialist",
    "shifty_shooter",
    "slippery_off_ball",
    "strong_handle",
    "unpluckable",
    "versatile_visionary",
])

# The 6 badges of NBA 2K25 that NBA 2K27 dropped. Kept as a named list because
# the migration and the tests both want to say "these must not appear in 2K27".
BADGES_DROPPED_IN_2K27 = [
    "boxout_beast",
    "on_ball_menace",
    "post_up_poet",
    "rebound_chaser",
    "set_shot_specialist",
    "shifty_shooter",
]

# The 19 badges NBA 2K27 added.
BADGES_NEW_IN_2K27 = [
    "ankle_braces",
    "arc_cadence",
    "boxout_boss",
    "breaker",
    "bruiser",
    "crasher",
    "flash",
    "ghost_stepper",
    "pace",
    "possession_closer",
    "post_spin_catalyst",
    "quick_trigger",
    "seatbelt",
    "set_and_fire",
    "smooth_operator",
    "static_middy",
    "sync_snatcher",
    "wall_up",
    "work_horse",
]

# 40 - 6 + 19 = 53.
_BADGES_2K27 = sorted(
    [key for key in _BADGES_2K25 if key not in BADGES_DROPPED_IN_2K27]
    + BADGES_NEW_IN_2K27
)

# --- The versions themselves -------------------------------------------------

GAME_VERSIONS = {
    "2K25": {
        "label": "NBA 2K25",
        "badges": _BADGES_2K25,
        "attributes": _ATTRIBUTES,
    },
    "2K26": {
        "label": "NBA 2K26",
        "badges": _BADGES_2K25,
        "attributes": _ATTRIBUTES,
    },
    "2K27": {
        "label": "NBA 2K27",
        "badges": _BADGES_2K27,
        "attributes": _ATTRIBUTES,
    },
}

# The version every player already in the database is stamped with.
# See docs/adr/0003-existing-players-stamped-2k26.md.
DEFAULT_GAME_VERSION = "2K26"


def is_valid_version(version):
    """
    True if `version` is a Game Version we know about.

    Deliberately exact: "2k27" is rejected, so a route can trust that anything
    that passes is spelled the way it is stored.
    """
    return version in GAME_VERSIONS


def all_versions():
    """Every Game Version key, oldest first - for the create-player dropdown."""
    return sorted(GAME_VERSIONS)


def version_label(version):
    """The name to show a user, e.g. "NBA 2K27"."""
    _require_version(version)
    return GAME_VERSIONS[version]["label"]


def badges_for(version):
    """The badge keys in `version`, in display order."""
    _require_version(version)
    return list(GAME_VERSIONS[version]["badges"])


def attributes_for(version):
    """The attribute keys in `version`, in display order."""
    _require_version(version)
    return list(GAME_VERSIONS[version]["attributes"])


def display_name(key):
    """
    The proper name for a badge or attribute key.

    Falls back to a title-cased key so an unknown key renders as something
    rather than blowing up a page.
    """
    if key in BADGE_NAMES:
        return BADGE_NAMES[key]
    if key in ATTRIBUTE_NAMES:
        return ATTRIBUTE_NAMES[key]
    return key.replace("_", " ").title()


def _require_version(version):
    if not is_valid_version(version):
        raise ValueError(f"Unknown game version: {version!r}")
