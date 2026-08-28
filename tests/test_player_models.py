"""
The Game Version aware Player shape: `Player.game_version`, and the
`PlayerAttribute` / `PlayerBadge` rows that replace the old wide columns.

These tests go through the models only. No route is involved, and no route
reads any of this yet.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.game_versions import DEFAULT_GAME_VERSION
from app.models import Player, PlayerAttribute, PlayerBadge, User, create_rows_for


@pytest.fixture
def player_owner(test_app):
    """A user to hang test players off. Players need an owner; nothing else."""
    user = User(
        username="owner",
        email="owner@example.com",
        password="not-a-real-hash",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def make_player(owner, version, name="Test Player"):
    """A saved Player in `version`, with no attribute or badge rows yet."""
    player = Player(name=name, user_id=owner.id, game_version=version)
    db.session.add(player)
    db.session.commit()
    return player


# --- Player.game_version -----------------------------------------------------

def test_a_player_remembers_its_game_version(player_owner):
    player = make_player(player_owner, "2K27")
    assert player.game_version == "2K27"


def test_an_unknown_game_version_is_rejected(player_owner):
    with pytest.raises(ValueError):
        Player(name="Nope", user_id=player_owner.id, game_version="2K24")


def test_a_player_created_without_a_version_is_stamped_the_default(player_owner):
    player = Player(name="Old Timer", user_id=player_owner.id)
    db.session.add(player)
    db.session.commit()
    assert player.game_version == DEFAULT_GAME_VERSION


# --- PlayerAttribute values --------------------------------------------------

@pytest.mark.parametrize("bad_value", [0, 24, 100])
def test_an_attribute_value_outside_25_to_99_is_rejected(player_owner, bad_value):
    player = make_player(player_owner, "2K26")
    with pytest.raises(ValueError):
        PlayerAttribute(player_id=player.id, attribute_key="agility", value=bad_value)


@pytest.mark.parametrize("boundary", [25, 99])
def test_the_boundary_attribute_values_are_accepted(player_owner, boundary):
    player = make_player(player_owner, "2K26")
    row = PlayerAttribute(player_id=player.id, attribute_key="agility", value=boundary)
    db.session.add(row)
    db.session.commit()
    assert row.value == boundary


@pytest.mark.parametrize("bad_value", [0, 24, 100])
def test_a_target_value_is_range_checked_the_same_way(player_owner, bad_value):
    player = make_player(player_owner, "2K26")
    with pytest.raises(ValueError):
        PlayerAttribute(
            player_id=player.id,
            attribute_key="agility",
            value=25,
            target_value=bad_value,
        )


def test_an_attribute_row_defaults_to_a_target_of_99(player_owner):
    player = make_player(player_owner, "2K26")
    row = PlayerAttribute(player_id=player.id, attribute_key="agility", value=25)
    db.session.add(row)
    db.session.commit()
    assert row.target_value == 99


def test_close_shot_is_range_checked_like_every_other_attribute(player_owner):
    """
    The old per-name @validates list left close_shot out entirely. One rule on
    one column makes that class of bug impossible; this pins it.
    """
    player = make_player(player_owner, "2K26")
    with pytest.raises(ValueError):
        PlayerAttribute(player_id=player.id, attribute_key="close_shot", value=100)


# --- PlayerBadge levels ------------------------------------------------------

def test_a_badge_level_outside_the_six_names_is_rejected(player_owner):
    """"Platinum" is a real badge level in other games, and not in this one."""
    player = make_player(player_owner, "2K26")
    with pytest.raises(ValueError):
        PlayerBadge(player_id=player.id, badge_key="deadeye", level="Platinum")


def test_a_real_badge_level_is_accepted(player_owner):
    player = make_player(player_owner, "2K26")
    row = PlayerBadge(player_id=player.id, badge_key="deadeye", level="Gold")
    db.session.add(row)
    db.session.commit()
    assert row.level == "Gold"


def test_a_target_level_is_checked_the_same_way(player_owner):
    player = make_player(player_owner, "2K26")
    with pytest.raises(ValueError):
        PlayerBadge(player_id=player.id, badge_key="deadeye", target_level="Platinum")


def test_a_badge_row_defaults_to_none_aiming_at_legendary(player_owner):
    player = make_player(player_owner, "2K26")
    row = PlayerBadge(player_id=player.id, badge_key="deadeye")
    db.session.add(row)
    db.session.commit()
    assert row.level == "None"
    assert row.target_level == "Legendary"


# --- create_rows_for: a complete player, in one call -------------------------

def test_a_2k27_player_gets_53_badge_rows_and_36_attribute_rows(player_owner):
    player = make_player(player_owner, "2K27")
    create_rows_for(player)
    db.session.commit()
    assert len(player.badges) == 53
    assert len(player.attributes) == 36


def test_a_2k26_player_gets_40_badge_rows(player_owner):
    player = make_player(player_owner, "2K26")
    create_rows_for(player)
    db.session.commit()
    assert len(player.badges) == 40
    assert len(player.attributes) == 36


def test_a_2k26_player_has_no_row_for_a_2k27_only_badge(player_owner):
    player = make_player(player_owner, "2K26")
    create_rows_for(player)
    db.session.commit()
    assert "ghost_stepper" not in {badge.badge_key for badge in player.badges}


def test_a_2k27_player_has_no_row_for_a_badge_2k27_dropped(player_owner):
    player = make_player(player_owner, "2K27")
    create_rows_for(player)
    db.session.commit()
    assert "shifty_shooter" not in {badge.badge_key for badge in player.badges}


def test_new_rows_start_at_the_bottom_aiming_at_the_top(player_owner):
    player = make_player(player_owner, "2K27")
    create_rows_for(player)
    db.session.commit()
    assert all(a.value == 25 and a.target_value == 99 for a in player.attributes)
    assert all(
        b.level == "None" and b.target_level == "Legendary" for b in player.badges
    )


# --- Cleanup and duplicates --------------------------------------------------

def test_deleting_a_player_deletes_all_its_attribute_and_badge_rows(player_owner):
    player = make_player(player_owner, "2K27")
    create_rows_for(player)
    db.session.commit()
    assert PlayerAttribute.query.count() == 36
    assert PlayerBadge.query.count() == 53

    db.session.delete(player)
    db.session.commit()

    assert PlayerAttribute.query.count() == 0
    assert PlayerBadge.query.count() == 0


def test_a_player_cannot_hold_the_same_badge_twice(player_owner):
    player = make_player(player_owner, "2K26")
    db.session.add(PlayerBadge(player_id=player.id, badge_key="deadeye"))
    db.session.commit()

    db.session.add(PlayerBadge(player_id=player.id, badge_key="deadeye"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_a_player_cannot_hold_the_same_attribute_twice(player_owner):
    player = make_player(player_owner, "2K26")
    db.session.add(PlayerAttribute(player_id=player.id, attribute_key="agility", value=25))
    db.session.commit()

    db.session.add(PlayerAttribute(player_id=player.id, attribute_key="agility", value=25))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_two_different_players_can_hold_the_same_badge(player_owner):
    """The unique rule is per player, not global."""
    one = make_player(player_owner, "2K26", name="One")
    two = make_player(player_owner, "2K26", name="Two")
    db.session.add(PlayerBadge(player_id=one.id, badge_key="deadeye"))
    db.session.add(PlayerBadge(player_id=two.id, badge_key="deadeye"))
    db.session.commit()
    assert PlayerBadge.query.count() == 2
