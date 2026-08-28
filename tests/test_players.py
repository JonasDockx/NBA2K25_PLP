"""
The four player screens, converted to read and write badge/attribute rows.

The tests that matter most here are the isolation test and the hostile POST
test: a 2K26 player must never be offered - or be able to reach - a badge that
only exists in 2K27, and the reverse. Everything else on these screens could
regress visibly and a user would notice; that one would regress silently.
"""

import pytest

from app import db
from app.game_versions import (
    BADGES_DROPPED_IN_2K27,
    BADGES_NEW_IN_2K27,
    attributes_for,
    badges_for,
)
from app.models import Player, PlayerAttribute, PlayerBadge, User


# --- fixtures ----------------------------------------------------------------


@pytest.fixture
def user(test_app):
    """A logged-in-able user who owns the players below."""
    user = User(
        username="owner",
        email="owner@example.com",
        password="not-a-real-hash",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in(client, user):
    """`client`, with `user` already logged in - no password round trip."""
    with client.session_transaction() as flask_session:
        flask_session["_user_id"] = str(user.id)
        flask_session["_fresh"] = True
    return client


def make_player(user, version="2K26", name="Tester", **columns):
    """A player of `version` with its full set of rows, straight into the db."""
    from app.models import create_rows_for

    player = Player(name=name, user_id=user.id, game_version=version, **columns)
    create_rows_for(player)
    db.session.add(player)
    db.session.commit()
    return player


def badge_row(player, key):
    return PlayerBadge.query.filter_by(player_id=player.id, badge_key=key).first()


def attribute_row(player, key):
    return PlayerAttribute.query.filter_by(player_id=player.id, attribute_key=key).first()


def create_form(version, **overrides):
    """A complete, valid create-player POST body."""
    form = {"name": "New Player", "game_version": version}
    form.update(overrides)
    return form


# --- 4a. creating a player ----------------------------------------------------


def test_creating_a_2k27_player_gets_53_badge_rows(logged_in):
    response = logged_in.post("/add_player", data=create_form("2K27"), follow_redirects=True)

    assert response.status_code == 200
    player = Player.query.filter_by(name="New Player").one()
    assert player.game_version == "2K27"
    assert len(player.badges) == 53
    assert len(player.attributes) == len(attributes_for("2K27"))


def test_creating_a_2k26_player_gets_40_badge_rows(logged_in):
    logged_in.post("/add_player", data=create_form("2K26"), follow_redirects=True)

    player = Player.query.filter_by(name="New Player").one()
    assert player.game_version == "2K26"
    assert len(player.badges) == 40


def test_a_2k27_player_has_the_new_badges_and_not_the_dropped_ones(logged_in):
    logged_in.post("/add_player", data=create_form("2K27"), follow_redirects=True)

    player = Player.query.filter_by(name="New Player").one()
    keys = {row.badge_key for row in player.badges}
    assert set(BADGES_NEW_IN_2K27) <= keys
    assert keys.isdisjoint(BADGES_DROPPED_IN_2K27)


def test_an_unknown_game_version_is_rejected_and_creates_no_player(logged_in):
    response = logged_in.post(
        "/add_player", data=create_form("2K24"), follow_redirects=True
    )

    assert response.status_code == 200
    assert Player.query.count() == 0
    assert PlayerBadge.query.count() == 0


def test_a_lowercase_game_version_is_rejected(logged_in):
    """is_valid_version is deliberately exact, and the route must not soften it."""
    logged_in.post("/add_player", data=create_form("2k27"), follow_redirects=True)

    assert Player.query.count() == 0


def test_creating_a_player_with_no_version_at_all_is_rejected(logged_in):
    response = logged_in.post(
        "/add_player", data={"name": "New Player"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert Player.query.count() == 0


def test_a_blank_name_is_rejected(logged_in):
    logged_in.post(
        "/add_player", data={"name": "   ", "game_version": "2K26"}, follow_redirects=True
    )

    assert Player.query.count() == 0


def test_submitted_attribute_values_land_on_the_rows(logged_in):
    logged_in.post(
        "/add_player",
        data=create_form("2K26", three_point_shot="87", speed="64"),
        follow_redirects=True,
    )

    player = Player.query.filter_by(name="New Player").one()
    assert attribute_row(player, "three_point_shot").value == 87
    assert attribute_row(player, "speed").value == 64
    # Anything not submitted keeps the floor create_rows_for set.
    assert attribute_row(player, "block").value == 25


def test_submitted_badge_levels_land_on_the_rows(logged_in):
    logged_in.post(
        "/add_player",
        data=create_form("2K27", ghost_stepper="Gold", deadeye="Silver"),
        follow_redirects=True,
    )

    player = Player.query.filter_by(name="New Player").one()
    assert badge_row(player, "ghost_stepper").level == "Gold"
    assert badge_row(player, "deadeye").level == "Silver"
    assert badge_row(player, "dimer").level == "None"


def test_a_badge_from_another_version_in_the_create_form_is_ignored(logged_in):
    """
    The create form renders every badge and hides the irrelevant ones, so a
    stale or scripted POST can carry a key this version does not have. It must
    be dropped, not create a row.
    """
    logged_in.post(
        "/add_player",
        data=create_form("2K26", ghost_stepper="Legendary"),
        follow_redirects=True,
    )

    player = Player.query.filter_by(name="New Player").one()
    assert badge_row(player, "ghost_stepper") is None
    assert len(player.badges) == 40


def test_an_out_of_range_attribute_is_rejected_and_creates_no_player(logged_in):
    response = logged_in.post(
        "/add_player", data=create_form("2K26", speed="250"), follow_redirects=True
    )

    assert response.status_code == 200
    assert Player.query.count() == 0
    assert PlayerAttribute.query.count() == 0


def test_a_non_numeric_attribute_is_rejected_and_creates_no_player(logged_in):
    logged_in.post(
        "/add_player", data=create_form("2K26", speed="fast"), follow_redirects=True
    )

    assert Player.query.count() == 0


def test_an_invalid_badge_level_is_rejected_and_creates_no_player(logged_in):
    logged_in.post(
        "/add_player",
        data=create_form("2K26", deadeye="Platinum"),
        follow_redirects=True,
    )

    assert Player.query.count() == 0


def test_the_create_form_offers_every_game_version(logged_in):
    page = logged_in.get("/add_player").get_data(as_text=True)

    assert 'value="2K25"' in page
    assert 'value="2K26"' in page
    assert 'value="2K27"' in page


def test_the_create_form_does_not_preselect_a_version(logged_in):
    """A silent default would create 2K26 players forever."""
    page = logged_in.get("/add_player").get_data(as_text=True)

    assert '<option value="" disabled selected>Select a Game Version</option>' in page


def test_the_create_form_tags_each_badge_with_the_versions_it_belongs_to(logged_in):
    page = logged_in.get("/add_player").get_data(as_text=True)

    # Shared by all three, dropped in 2K27, and new in 2K27 respectively.
    assert 'data-versions="2K25 2K26 2K27"' in page
    assert 'data-versions="2K25 2K26"' in page
    assert 'data-versions="2K27"' in page


# --- 4b. the isolation and hostile-POST tests --------------------------------


def test_the_upgrade_page_hides_2k27_badges_from_a_2k26_player(logged_in, user):
    player = make_player(user, "2K26")

    page = logged_in.get(f"/upgrade_attribute?player_id={player.id}").get_data(as_text=True)

    assert "Ghost Stepper" not in page
    assert "ghost_stepper" not in page
    assert "Shifty Shooter" in page


def test_the_upgrade_page_shows_2k27_badges_to_a_2k27_player(logged_in, user):
    player = make_player(user, "2K27")

    page = logged_in.get(f"/upgrade_attribute?player_id={player.id}").get_data(as_text=True)

    assert "Ghost Stepper" in page
    assert "Shifty Shooter" not in page
    assert "shifty_shooter" not in page


def test_a_2k26_player_cannot_upgrade_a_2k27_badge_by_hand_crafting_a_post(logged_in, user):
    player = make_player(user, "2K26", devpoints=100)

    response = logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "badge_devpoints": "ghost_stepper"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert badge_row(player, "ghost_stepper") is None
    # Refused outright: no row created, and nothing paid for it.
    assert player.devpoints == 100


def test_a_2k27_player_cannot_upgrade_a_dropped_2k26_badge(logged_in, user):
    player = make_player(user, "2K27", devpoints=100)

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "badge_devpoints": "shifty_shooter"},
        follow_redirects=True,
    )

    assert badge_row(player, "shifty_shooter") is None
    assert player.devpoints == 100


def test_a_badgepoint_upgrade_of_a_foreign_badge_is_refused_too(logged_in, user):
    player = make_player(user, "2K26", badgepoints=5)

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "badge_badgepoints": "ghost_stepper"},
        follow_redirects=True,
    )

    assert badge_row(player, "ghost_stepper") is None
    assert player.badgepoints == 5


def test_an_attribute_that_does_not_exist_is_refused(logged_in, user):
    player = make_player(user, "2K26", devpoints=100)

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "attribute": "dribbling_wizardry"},
        follow_redirects=True,
    )

    assert player.devpoints == 100


# --- 4b. the economy, unchanged ----------------------------------------------


def test_upgrading_a_badge_costs_the_right_points_and_lands_on_the_next_level(logged_in, user):
    player = make_player(user, "2K27", devpoints=10)

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "badge_devpoints": "ghost_stepper"},
        follow_redirects=True,
    )

    # "None" -> "Bronze" costs 3.
    assert badge_row(player, "ghost_stepper").level == "Bronze"
    assert player.devpoints == 7


def test_upgrading_a_badge_with_a_badge_point_costs_one_point(logged_in, user):
    player = make_player(user, "2K26", badgepoints=2)

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "badge_badgepoints": "deadeye"},
        follow_redirects=True,
    )

    assert badge_row(player, "deadeye").level == "Bronze"
    assert player.badgepoints == 1


def test_a_legendary_badge_cannot_be_upgraded_further(logged_in, user):
    player = make_player(user, "2K26", devpoints=100)
    badge_row(player, "deadeye").level = "Legendary"
    db.session.commit()

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "badge_devpoints": "deadeye"},
        follow_redirects=True,
    )

    assert badge_row(player, "deadeye").level == "Legendary"
    assert player.devpoints == 100


def test_upgrading_an_attribute_at_98_works(logged_in, user):
    player = make_player(user, "2K26", devpoints=100)
    attribute_row(player, "speed").value = 98
    db.session.commit()

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "attribute": "speed"},
        follow_redirects=True,
    )

    assert attribute_row(player, "speed").value == 99
    # Above 90 costs 5.
    assert player.devpoints == 95


def test_upgrading_an_attribute_at_99_is_refused(logged_in, user):
    player = make_player(user, "2K26", devpoints=100)
    attribute_row(player, "speed").value = 99
    db.session.commit()

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "attribute": "speed"},
        follow_redirects=True,
    )

    assert attribute_row(player, "speed").value == 99
    assert player.devpoints == 100


def test_an_upgrade_without_enough_devpoints_changes_nothing(logged_in, user):
    player = make_player(user, "2K26", devpoints=0)

    logged_in.post(
        "/upgrade_attribute",
        data={"player_id": player.id, "attribute": "speed"},
        follow_redirects=True,
    )

    assert attribute_row(player, "speed").value == 25
    assert player.devpoints == 0


# --- ownership, which the conversion must not lose ---------------------------


def other_users_player(version="2K26"):
    stranger = User(
        username="stranger",
        email="stranger@example.com",
        password="not-a-real-hash",
        is_active=True,
    )
    db.session.add(stranger)
    db.session.commit()
    return make_player(stranger, version, name="Not Yours")


def test_a_user_cannot_upgrade_another_users_player(logged_in, user):
    theirs = other_users_player()

    response = logged_in.post(
        "/upgrade_attribute",
        data={"player_id": theirs.id, "attribute": "speed"},
    )

    assert response.status_code == 403
    assert attribute_row(theirs, "speed").value == 25


def test_a_user_cannot_view_another_users_upgrade_page(logged_in, user):
    theirs = other_users_player()

    assert logged_in.get(f"/upgrade_attribute?player_id={theirs.id}").status_code == 403


def test_a_user_cannot_edit_another_users_player(logged_in, user):
    theirs = other_users_player()

    assert logged_in.get(f"/edit_player?player_id={theirs.id}").status_code == 403


def test_a_user_cannot_set_targets_on_another_users_player(logged_in, user):
    theirs = other_users_player()

    response = logged_in.post(
        "/target_settings", data={"player_id": theirs.id, "save_targets": "Save"}
    )

    assert response.status_code == 403


# --- 4c. targets --------------------------------------------------------------


def test_setting_targets_saves_to_the_right_rows(logged_in, user):
    player = make_player(user, "2K27")

    form = {"player_id": player.id, "save_targets": "Save"}
    for key in attributes_for("2K27"):
        form[f"target_{key}"] = 80
    for key in badges_for("2K27"):
        form[f"target_{key}"] = "Gold"
    form["target_three_point_shot"] = 95
    form["target_ghost_stepper"] = "Hall of Fame"

    logged_in.post("/target_settings", data=form, follow_redirects=True)

    assert attribute_row(player, "three_point_shot").target_value == 95
    assert attribute_row(player, "speed").target_value == 80
    assert badge_row(player, "ghost_stepper").target_level == "Hall of Fame"
    assert badge_row(player, "deadeye").target_level == "Gold"


def test_an_out_of_range_target_is_rejected_and_saves_nothing(logged_in, user):
    player = make_player(user, "2K26")

    form = {"player_id": player.id, "save_targets": "Save"}
    for key in attributes_for("2K26"):
        form[f"target_{key}"] = 80
    form["target_speed"] = 250

    logged_in.post("/target_settings", data=form, follow_redirects=True)

    # Nothing was written - not even the valid fields ahead of the bad one.
    assert attribute_row(player, "speed").target_value == 99
    assert attribute_row(player, "block").target_value == 99


def test_an_invalid_target_badge_level_is_rejected_and_saves_nothing(logged_in, user):
    player = make_player(user, "2K26")

    form = {"player_id": player.id, "save_targets": "Save"}
    for key in attributes_for("2K26"):
        form[f"target_{key}"] = 80
    for key in badges_for("2K26"):
        form[f"target_{key}"] = "Gold"
    form["target_deadeye"] = "Platinum"

    logged_in.post("/target_settings", data=form, follow_redirects=True)

    assert badge_row(player, "deadeye").target_level == "Legendary"
    assert attribute_row(player, "speed").target_value == 99


def test_the_targets_page_only_offers_the_players_own_badges(logged_in, user):
    player = make_player(user, "2K26")

    page = logged_in.get(f"/target_settings?player_id={player.id}").get_data(as_text=True)

    assert "target_ghost_stepper" not in page
    assert "target_shifty_shooter" in page


def test_the_targets_page_fills_the_form_in_after_a_save(logged_in, user):
    """The save redirects back here with the id in the URL, so the GET must load."""
    player = make_player(user, "2K26")
    attribute_row(player, "speed").target_value = 88
    db.session.commit()

    page = logged_in.get(f"/target_settings?player_id={player.id}").get_data(as_text=True)

    assert 'value="88"' in page


# --- 4d. editing (the Correction tool) ---------------------------------------


def edit_form(player, **overrides):
    """A complete, valid edit POST body for `player`."""
    form = {"player_id": player.id, "name": player.name}
    for key in attributes_for(player.game_version):
        form[key] = 50
    for key in badges_for(player.game_version):
        form[key] = "None"
    form.update(overrides)
    return form


def test_editing_saves_every_attribute_not_just_the_first(logged_in, user):
    """
    The old route had the save block nested inside the attribute loop, so it
    committed and returned on the first iteration and only agility was ever
    written. This pins the fix.
    """
    player = make_player(user, "2K26")

    logged_in.post(
        "/edit_player",
        data=edit_form(player, agility=71, speed=72, vertical=73),
        follow_redirects=True,
    )

    assert attribute_row(player, "agility").value == 71
    assert attribute_row(player, "speed").value == 72
    assert attribute_row(player, "vertical").value == 73


def test_editing_writes_values_directly_outside_the_economy(logged_in, user):
    """The Correction tool bypasses devpoints entirely - ADR 0001."""
    player = make_player(user, "2K26", devpoints=0)

    logged_in.post(
        "/edit_player", data=edit_form(player, speed=95), follow_redirects=True
    )

    assert attribute_row(player, "speed").value == 95
    assert player.devpoints == 0


def test_editing_saves_badge_levels(logged_in, user):
    player = make_player(user, "2K27")

    logged_in.post(
        "/edit_player",
        data=edit_form(player, ghost_stepper="Hall of Fame"),
        follow_redirects=True,
    )

    assert badge_row(player, "ghost_stepper").level == "Hall of Fame"


def test_editing_renames_the_player(logged_in, user):
    player = make_player(user, "2K26")

    logged_in.post(
        "/edit_player", data=edit_form(player, name="Renamed"), follow_redirects=True
    )

    assert player.name == "Renamed"


def test_the_edit_page_only_offers_the_players_own_badges(logged_in, user):
    player = make_player(user, "2K27")

    page = logged_in.get(f"/edit_player?player_id={player.id}").get_data(as_text=True)

    assert "Ghost Stepper" in page
    assert "Shifty Shooter" not in page


def test_an_out_of_range_edit_is_refused_with_a_flash_not_a_500(logged_in, user):
    player = make_player(user, "2K26")

    response = logged_in.post(
        "/edit_player", data=edit_form(player, speed=250), follow_redirects=True
    )

    assert response.status_code == 200
    assert attribute_row(player, "speed").value == 25


def test_a_non_numeric_edit_is_refused_and_saves_nothing(logged_in, user):
    player = make_player(user, "2K26")

    logged_in.post(
        "/edit_player", data=edit_form(player, speed="fast"), follow_redirects=True
    )

    assert attribute_row(player, "speed").value == 25
    assert attribute_row(player, "agility").value == 25


def test_an_invalid_badge_level_in_an_edit_is_refused(logged_in, user):
    player = make_player(user, "2K26")

    logged_in.post(
        "/edit_player", data=edit_form(player, deadeye="Platinum"), follow_redirects=True
    )

    assert badge_row(player, "deadeye").level == "None"
    assert attribute_row(player, "speed").value == 25


def test_a_blank_name_in_an_edit_is_refused(logged_in, user):
    player = make_player(user, "2K26")

    logged_in.post(
        "/edit_player", data=edit_form(player, name="  "), follow_redirects=True
    )

    assert player.name == "Tester"


# --- 4e. the read-only version label -----------------------------------------


@pytest.mark.parametrize("path", ["/upgrade_attribute", "/edit_player", "/target_settings"])
def test_every_player_screen_shows_the_game_version(logged_in, user, path):
    player = make_player(user, "2K27")

    page = logged_in.get(f"{path}?player_id={player.id}").get_data(as_text=True)

    assert "Game Version: NBA 2K27" in page


@pytest.mark.parametrize("path", ["/upgrade_attribute", "/edit_player", "/target_settings"])
def test_no_screen_offers_a_way_to_change_the_game_version(logged_in, user, path):
    """By design: to play a different game you create a new player."""
    player = make_player(user, "2K26")

    page = logged_in.get(f"{path}?player_id={player.id}").get_data(as_text=True)

    assert 'name="game_version"' not in page


# --- display names, which .title() used to guess wrong ------------------------


def test_the_screens_use_the_proper_display_names(logged_in, user):
    player = make_player(user, "2K26")

    page = logged_in.get(f"/upgrade_attribute?player_id={player.id}").get_data(as_text=True)

    assert "High-Flying Denier" in page
    assert "High Flying Denier" not in page
    assert "Three-Point Shot" in page
    assert "Pass IQ" in page
    assert "Handles for Days" in page
