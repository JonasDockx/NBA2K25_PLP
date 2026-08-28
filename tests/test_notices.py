"""
Issue 05: the dashboard changeover notice and the 2Kratings warning.

The two copy tests are deliberately thin - they check that the notice is on the
page at all, not how it is worded, because pinning wording down makes rewording
it annoying and a typo is not a regression worth a red build.

The scrape tests are not thin. Nothing about the ratings warning changes what
the scraper does, so the risk in this issue is that the extra markup breaks the
import that fills the form. That import finds attribute inputs by element `id`
and badge selects by `name`, so what has to stay true is that those fields
exist, with those identifiers, for both a 2K26 and a 2K27 player.
"""

import pytest

from app import db
from app.game_versions import (
    BADGES_DROPPED_IN_2K27,
    BADGES_NEW_IN_2K27,
    attributes_for,
    badges_for,
)
from app.models import User


@pytest.fixture
def logged_in(client, test_app):
    """A logged-in browser - the create form and dashboard both require one."""
    user = User(
        username="reader",
        email="reader@example.com",
        password="not-a-real-hash",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as flask_session:
        flask_session["_user_id"] = str(user.id)
        flask_session["_fresh"] = True
    return client


# --- 5a. the dashboard notice -------------------------------------------------


def test_dashboard_carries_the_changeover_notice(logged_in):
    response = logged_in.get("/dashboard")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'class="version-notice"' in page
    assert "NBA 2K26" in page
    assert "NBA 2K27" in page


def test_the_notice_is_not_an_alert(logged_in):
    """
    base.html hides every element with class `alert` five seconds after load.
    That is right for a flash message and wrong for this, which has to stay
    readable - so the notice must not borrow that class.
    """
    page = logged_in.get("/dashboard").get_data(as_text=True)

    notice = page[page.index('class="version-notice"') :]
    notice = notice[: notice.index("</div>")]
    assert "alert" not in notice


# --- 5b. the scrape warning ---------------------------------------------------


def test_create_form_carries_the_scrape_warning(logged_in):
    response = logged_in.get("/add_player")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'class="scrape-warning"' in page
    assert "NBA 2K27" in page


def test_the_warning_sits_with_the_scrape_button_not_the_create_button(logged_in):
    """
    A warning about imported ratings is useless further down the page than the
    button that imports them.
    """
    page = logged_in.get("/add_player").get_data(as_text=True)

    assert page.index("Fetch Player Data") < page.index('class="scrape-warning"')
    assert page.index('class="scrape-warning"') < page.index("Add Player")


# --- 5b. the scrape path still fills the form ---------------------------------


def scraped_payload():
    """
    What the scraper hands back: 2K27 numbers, 35 attributes rather than 36
    (2Kratings has never published `intangibles`), and badges spanning both the
    ones 2K27 added and the ones it dropped - a real page would not contain the
    dropped ones, but sending them proves the older form still copes.
    """
    attributes = {
        key: 80 for key in attributes_for("2K26") if key != "intangibles"
    }
    badges = {key: "Gold" for key in badges_for("2K27")}
    badges.update({key: "Silver" for key in BADGES_DROPPED_IN_2K27})
    return {"player_name": "Imported Player", "attributes": attributes, "badges": badges}


@pytest.fixture
def fake_scrape(monkeypatch):
    """The scraper, without the network. Patched where routes.py looks it up."""
    import app.routes

    payload = scraped_payload()
    monkeypatch.setattr(app.routes, "scrape_player_data", lambda part: payload)
    return payload


def test_scrape_endpoint_returns_the_player_data(logged_in, fake_scrape):
    response = logged_in.post("/scrape_player", json={"player_url_part": "lebron-james"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["player_data"]["player_name"] == "Imported Player"


def test_scrape_returns_35_attributes_and_never_intangibles(logged_in, fake_scrape):
    """
    Pre-existing 2Kratings behaviour, pinned here so the form is not later
    "fixed" to look as though intangibles was imported when it was not.
    """
    body = logged_in.post("/scrape_player", json={"player_url_part": "x"}).get_json()

    attributes = body["player_data"]["attributes"]
    assert len(attributes) == 35
    assert "intangibles" not in attributes


def test_intangibles_keeps_its_default_on_the_form(logged_in):
    """The one attribute the import cannot fill must still be sitting at 25."""
    page = logged_in.get("/add_player").get_data(as_text=True)

    assert 'id="intangibles"' in page
    field = page[page.index('id="intangibles"') :]
    assert 'value="25"' in field[: field.index(">") + 1]


@pytest.mark.parametrize("version", ["2K26", "2K27"])
def test_every_scraped_attribute_has_a_field_the_import_can_fill(logged_in, version):
    """
    The import sets attribute inputs by element id. Attributes do not vary by
    Game Version, so this must hold for both.
    """
    page = logged_in.get("/add_player").get_data(as_text=True)

    for key in scraped_payload()["attributes"]:
        assert f'id="{key}"' in page, f"{key} has no input for {version} to fill"


@pytest.mark.parametrize("version", ["2K26", "2K27"])
def test_every_badge_of_the_version_has_a_select_the_import_can_fill(logged_in, version):
    """
    The import sets badge selects by name. Every badge belonging to `version`
    must therefore be rendered and tagged as belonging to it, or a scraped
    value would land nowhere.
    """
    page = logged_in.get("/add_player").get_data(as_text=True)

    for key in badges_for(version):
        assert f'name="{key}"' in page, f"{key} has no select on the form"

    # and the ones that version does not have are tagged for the other one, so
    # the filter hides them and a scraped value for them is simply dropped.
    absent = BADGES_NEW_IN_2K27 if version == "2K26" else BADGES_DROPPED_IN_2K27
    for key in absent:
        block = page[: page.index(f'name="{key}"')]
        tag = block[block.rindex("data-versions=") :]
        assert version not in tag.split('"')[1].split(), (
            f"{key} is offered to {version} but does not exist there"
        )
