"""
Tests for scripts/drop_old_player_columns.py - the second, deferred half of
step 3.

Both routes through the script are covered: ALTER TABLE DROP COLUMN, and the
create/copy/rename rebuild that older SQLite needs. The laptop has a modern
SQLite, so the rebuild path is forced with --force-rebuild rather than left
untested until the day the server turns out to be old.
"""

import importlib.util
import os
import sqlite3

import pytest

from app import game_versions as gv

from tests.test_migration import (
    add_player,
    add_targets,
    migrate_script,
    old_database,  # noqa: F401 - fixture
    old_database_path,  # noqa: F401 - fixture
    run_migration,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, "scripts", "drop_old_player_columns.py")
_spec = importlib.util.spec_from_file_location("_drop", _SCRIPT)
drop_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drop_script)

ATTRIBUTES = gv.attributes_for("2K26")
BADGES = gv.badges_for("2K26")


def run_drop(path, extra=None):
    """Run the script's main(), answering its confirmation prompt with "drop"."""
    import builtins
    real_input = builtins.input
    builtins.input = lambda *_: "drop"
    try:
        return drop_script.main([path] + (extra or []))
    finally:
        builtins.input = real_input


# --- What it drops -----------------------------------------------------------

def test_columns_to_drop_finds_the_old_wide_columns(old_database):
    columns = drop_script.columns_to_drop(old_database, gv)

    assert len(columns) == len(ATTRIBUTES) + len(BADGES)
    assert "agility" in columns
    assert "deadeye" in columns
    # The columns that must survive.
    assert "id" not in columns
    assert "name" not in columns
    assert "user_id" not in columns
    assert "devpoints" not in columns
    assert "badgepoints" not in columns


@pytest.mark.parametrize("extra", [[], ["--force-rebuild"]])
def test_old_columns_and_targets_are_gone_afterwards(
        old_database, old_database_path, extra):
    """Both the in-place drop and the rebuild reach the same end state."""
    add_player(old_database, 1, "Keeper", attributes={"agility": 88})
    add_targets(old_database, 1, attributes={"agility": 95})
    run_migration(old_database)
    old_database.close()

    assert run_drop(old_database_path, extra) == 0

    conn = sqlite3.connect(old_database_path)
    columns = migrate_script.column_names(conn, "player")
    assert "agility" not in columns
    assert "deadeye" not in columns
    assert "player_targets" not in migrate_script.table_names(conn)
    conn.close()


@pytest.mark.parametrize("extra", [[], ["--force-rebuild"]])
def test_the_columns_that_matter_survive(old_database, old_database_path, extra):
    add_player(old_database, 1, "Survivor")
    old_database.execute("UPDATE player SET devpoints = 42, badgepoints = 7")
    run_migration(old_database)
    old_database.close()

    assert run_drop(old_database_path, extra) == 0

    conn = sqlite3.connect(old_database_path)
    row = conn.execute(
        "SELECT id, name, user_id, devpoints, badgepoints, game_version "
        "FROM player").fetchone()
    assert row == (1, "Survivor", 1, 42, 7, "2K26")
    conn.close()


@pytest.mark.parametrize("extra", [[], ["--force-rebuild"]])
def test_the_new_rows_are_untouched(old_database, old_database_path, extra):
    """Dropping the source columns must not disturb the copy."""
    add_player(old_database, 1, attributes={"agility": 73},
               badges={"deadeye": "Gold"})
    run_migration(old_database)
    before_attributes = old_database.execute(
        "SELECT player_id, attribute_key, value, target_value "
        "FROM player_attribute ORDER BY id").fetchall()
    before_badges = old_database.execute(
        "SELECT player_id, badge_key, level, target_level "
        "FROM player_badge ORDER BY id").fetchall()
    old_database.close()

    assert run_drop(old_database_path, extra) == 0

    conn = sqlite3.connect(old_database_path)
    assert conn.execute(
        "SELECT player_id, attribute_key, value, target_value "
        "FROM player_attribute ORDER BY id").fetchall() == before_attributes
    assert conn.execute(
        "SELECT player_id, badge_key, level, target_level "
        "FROM player_badge ORDER BY id").fetchall() == before_badges
    conn.close()


@pytest.mark.parametrize("extra", [[], ["--force-rebuild"]])
def test_no_player_or_user_is_lost(old_database, old_database_path, extra):
    for player_id in range(1, 6):
        add_player(old_database, player_id, f"P{player_id}")
    run_migration(old_database)
    old_database.close()

    assert run_drop(old_database_path, extra) == 0

    conn = sqlite3.connect(old_database_path)
    assert conn.execute("SELECT COUNT(*) FROM player").fetchone()[0] == 5
    assert conn.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 1
    assert [r[0] for r in conn.execute(
        "SELECT name FROM player ORDER BY id")] == [f"P{i}" for i in range(1, 6)]
    conn.close()


@pytest.mark.parametrize("extra", [[], ["--force-rebuild"]])
def test_cascade_still_works_afterwards(old_database, old_database_path, extra):
    """
    The rebuild path recreates the table and its foreign key. Deleting a player
    must still take its rows with it, or the app leaks orphans forever.
    """
    add_player(old_database, 1)
    run_migration(old_database)
    old_database.close()

    assert run_drop(old_database_path, extra) == 0

    conn = sqlite3.connect(old_database_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM player WHERE id = 1")
    conn.commit()
    assert conn.execute(
        "SELECT COUNT(*) FROM player_attribute").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM player_badge").fetchone()[0] == 0
    conn.close()


# --- When it must refuse -----------------------------------------------------

def test_refuses_on_a_database_that_was_never_migrated(
        old_database, old_database_path):
    add_player(old_database, 1)
    old_database.close()

    assert run_drop(old_database_path) == 2

    conn = sqlite3.connect(old_database_path)
    assert "agility" in migrate_script.column_names(conn, "player")
    conn.close()


def test_refuses_when_a_player_has_no_rows(old_database, old_database_path):
    """
    The whole point of the safety check: a player whose data never made it
    across must stop the drop, because dropping would lose that player's data
    for good.
    """
    add_player(old_database, 1)
    add_player(old_database, 2)
    run_migration(old_database)
    old_database.execute("DELETE FROM player_attribute WHERE player_id = 2")
    old_database.close()

    assert run_drop(old_database_path) == 2

    conn = sqlite3.connect(old_database_path)
    assert "agility" in migrate_script.column_names(conn, "player")
    conn.close()


def test_a_second_run_has_nothing_to_do(old_database, old_database_path):
    add_player(old_database, 1)
    run_migration(old_database)
    old_database.close()

    assert run_drop(old_database_path) == 0
    assert run_drop(old_database_path) == 1


def test_answering_the_prompt_with_anything_else_stops(
        old_database, old_database_path):
    import builtins
    add_player(old_database, 1)
    run_migration(old_database)
    old_database.close()

    real_input = builtins.input
    builtins.input = lambda *_: "no"
    try:
        assert drop_script.main([old_database_path]) == 1
    finally:
        builtins.input = real_input

    conn = sqlite3.connect(old_database_path)
    assert "agility" in migrate_script.column_names(conn, "player")
    conn.close()


# --- Version detection -------------------------------------------------------

def test_supports_drop_column_matches_this_sqlite():
    version = tuple(int(p) for p in sqlite3.sqlite_version.split("."))
    assert drop_script.supports_drop_column() == (version >= (3, 35, 0))
