"""
Tests for app/game_versions.py.

No database, no Flask app, no fixtures - this module is plain data, so these
run in milliseconds. The counting tests look trivial, but a 53-item list is
exactly the kind of thing a copy-paste slip hides in.
"""

import pytest

from app.game_versions import (
    ATTRIBUTE_NAMES,
    BADGES_DROPPED_IN_2K27,
    BADGES_NEW_IN_2K27,
    BADGE_LEVELS,
    BADGE_NAMES,
    BADGE_UPGRADE_COSTS,
    DEFAULT_GAME_VERSION,
    all_versions,
    attribute_upgrade_cost,
    attributes_for,
    badge_upgrade_cost,
    badges_for,
    display_name,
    is_valid_version,
    next_badge_level,
    version_label,
)

ALL = ["2K25", "2K26", "2K27"]

# The 34 badges that exist in both the old set and 2K27.
CARRIED_OVER = [
    "aerial_wizard", "ankle_assassin", "bail_out", "break_starter",
    "brick_wall", "challenger", "deadeye", "dimer", "float_game", "glove",
    "handles_for_days", "high_flying_denier", "hook_specialist",
    "immovable_enforcer", "interceptor", "layup_mixmaster", "lightning_launch",
    "limitless_range", "mini_marksman", "off_ball_pest", "paint_patroller",
    "paint_prodigy", "physical_finisher", "pick_dodger", "pogo_stick",
    "post_fade_phenom", "post_lockdown", "post_powerhouse", "posterizer",
    "rise_up", "slippery_off_ball", "strong_handle", "unpluckable",
    "versatile_visionary",
]


# --- Versions ----------------------------------------------------------------

def test_there_are_exactly_three_versions():
    assert all_versions() == ALL


def test_every_version_has_a_label():
    assert version_label("2K25") == "NBA 2K25"
    assert version_label("2K26") == "NBA 2K26"
    assert version_label("2K27") == "NBA 2K27"


def test_default_game_version_is_a_real_version():
    # Existing players get stamped with this one, per ADR 0003.
    assert DEFAULT_GAME_VERSION == "2K26"
    assert is_valid_version(DEFAULT_GAME_VERSION)


@pytest.mark.parametrize("version", ALL)
def test_is_valid_version_accepts_the_real_versions(version):
    assert is_valid_version(version)


@pytest.mark.parametrize("bad", ["2K24", "2K28", "", None, "2k27", " 2K27", 2027])
def test_is_valid_version_rejects_everything_else(bad):
    # Matching is exact on purpose, so lowercase "2k27" is a rejection.
    assert not is_valid_version(bad)


@pytest.mark.parametrize("bad", ["2K24", "", None, "2k27"])
def test_lookups_refuse_an_unknown_version(bad):
    for lookup in (badges_for, attributes_for, version_label):
        with pytest.raises(ValueError):
            lookup(bad)


# --- Badge counts ------------------------------------------------------------

def test_old_versions_have_forty_badges():
    assert len(badges_for("2K25")) == 40
    assert len(badges_for("2K26")) == 40


def test_2k27_has_fifty_three_badges():
    assert len(badges_for("2K27")) == 53


def test_2k25_and_2k26_share_a_badge_list():
    assert badges_for("2K25") == badges_for("2K26")


def test_the_arithmetic_holds():
    # 34 carried over + 19 new = 53, and 34 + 6 dropped = 40.
    assert len(CARRIED_OVER) == 34
    assert len(BADGES_NEW_IN_2K27) == 19
    assert len(BADGES_DROPPED_IN_2K27) == 6
    assert len(CARRIED_OVER) + len(BADGES_NEW_IN_2K27) == 53
    assert len(CARRIED_OVER) + len(BADGES_DROPPED_IN_2K27) == 40


@pytest.mark.parametrize("version", ALL)
def test_no_duplicate_badge_keys(version):
    badges = badges_for(version)
    assert len(badges) == len(set(badges))


# --- Badge membership --------------------------------------------------------

@pytest.mark.parametrize("badge", BADGES_DROPPED_IN_2K27)
def test_dropped_badges_are_gone_from_2k27(badge):
    assert badge not in badges_for("2K27")
    assert badge in badges_for("2K25")
    assert badge in badges_for("2K26")


@pytest.mark.parametrize("badge", BADGES_NEW_IN_2K27)
def test_new_badges_are_only_in_2k27(badge):
    assert badge in badges_for("2K27")
    assert badge not in badges_for("2K25")
    assert badge not in badges_for("2K26")


@pytest.mark.parametrize("badge", CARRIED_OVER)
def test_carried_over_badges_are_in_every_version(badge):
    for version in ALL:
        assert badge in badges_for(version)


def test_boxout_beast_is_not_silently_renamed_to_boxout_boss():
    # They are replacements, not renames: nothing carries over between them.
    assert "boxout_beast" in badges_for("2K25")
    assert "boxout_beast" not in badges_for("2K27")
    assert "boxout_boss" in badges_for("2K27")
    assert "boxout_boss" not in badges_for("2K25")


def test_the_2k27_badge_list_is_exactly_carried_over_plus_new():
    assert badges_for("2K27") == sorted(CARRIED_OVER + BADGES_NEW_IN_2K27)


# --- Attributes --------------------------------------------------------------

@pytest.mark.parametrize("version", ALL)
def test_every_version_has_thirty_six_attributes(version):
    assert len(attributes_for(version)) == 36


def test_attributes_are_identical_in_every_version():
    assert attributes_for("2K25") == attributes_for("2K26") == attributes_for("2K27")


def test_intangibles_is_still_an_attribute():
    # 2Kratings never provides it, but the app has always tracked it.
    assert "intangibles" in attributes_for("2K27")


# --- Display names -----------------------------------------------------------

@pytest.mark.parametrize("version", ALL)
def test_every_badge_and_attribute_has_a_real_display_name(version):
    for key in badges_for(version) + attributes_for(version):
        name = display_name(key)
        assert name, f"{key} has no display name"
        assert name.strip() == name, f"{key} display name has stray whitespace"
        assert "_" not in name, f"{key} display name still looks like a key"


def test_no_stray_names_defined_for_badges_that_do_not_exist():
    known = set(badges_for("2K25")) | set(badges_for("2K27"))
    assert set(BADGE_NAMES) == known


def test_attribute_names_cover_exactly_the_attributes():
    assert set(ATTRIBUTE_NAMES) == set(attributes_for("2K25"))


@pytest.mark.parametrize(
    "key,expected",
    [
        ("high_flying_denier", "High-Flying Denier"),
        ("off_ball_pest", "Off-Ball Pest"),
        ("on_ball_menace", "On-Ball Menace"),
        ("slippery_off_ball", "Slippery Off-Ball"),
        ("handles_for_days", "Handles for Days"),
        ("set_and_fire", "Set and Fire"),
        ("three_point_shot", "Three-Point Shot"),
        ("mid_range_shot", "Mid-Range Shot"),
        ("speed_with_ball", "Speed with Ball"),
        ("pass_iq", "Pass IQ"),
        ("shot_iq", "Shot IQ"),
        ("help_defense_iq", "Help Defense IQ"),
    ],
)
def test_the_names_title_case_used_to_get_wrong(key, expected):
    assert display_name(key) == expected


def test_display_name_falls_back_for_an_unknown_key():
    assert display_name("some_new_badge") == "Some New Badge"


# --- Badge levels ------------------------------------------------------------

def test_badge_levels_are_the_six_names_in_order():
    assert BADGE_LEVELS == [
        "None", "Bronze", "Silver", "Gold", "Hall of Fame", "Legendary"
    ]
    assert BADGE_LEVELS[0] == "None"
    assert BADGE_LEVELS[-1] == "Legendary"


@pytest.mark.parametrize(
    "level,expected",
    [
        ("None", "Bronze"),
        ("Bronze", "Silver"),
        ("Silver", "Gold"),
        ("Gold", "Hall of Fame"),
        ("Hall of Fame", "Legendary"),
        ("Legendary", None),
        ("Platinum", None),
    ],
)
def test_next_badge_level(level, expected):
    assert next_badge_level(level) == expected


# --- Upgrade costs -----------------------------------------------------------

@pytest.mark.parametrize(
    "level,cost",
    [
        ("None", 3),
        ("Bronze", 5),
        ("Silver", 7),
        ("Gold", 10),
        ("Hall of Fame", 20),
    ],
)
def test_badge_upgrade_costs_match_the_old_routes(level, cost):
    assert badge_upgrade_cost(level) == cost


def test_legendary_has_no_upgrade_cost():
    assert badge_upgrade_cost("Legendary") is None
    assert "Legendary" not in BADGE_UPGRADE_COSTS


@pytest.mark.parametrize(
    "value,cost",
    [
        (25, 1), (69, 1),
        (70, 2), (79, 2),
        (80, 3), (89, 3),
        (90, 5), (98, 5),
    ],
)
def test_attribute_upgrade_costs_match_the_old_routes(value, cost):
    assert attribute_upgrade_cost(value) == cost
