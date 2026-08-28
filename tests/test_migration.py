"""
Tests for scripts/migrate_to_game_versions.py.

The awkward part of testing a migration is that the models have already moved
on: there is no way to ask SQLAlchemy for the OLD shape any more. So these
tests build an old-shaped database with raw SQL - the 36 attribute columns and
40 badge columns generated from app/game_versions.py rather than typed out -
put a few players in it, run the migration against it, and assert on what comes
out the other side.
"""

import importlib.util
import os
import sqlite3

import pytest

from app import game_versions as gv

# The script is not a package, so it is loaded by path.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, "scripts", "migrate_to_game_versions.py")
_spec = importlib.util.spec_from_file_location("_migrate", _SCRIPT)
migrate_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migrate_script)

ATTRIBUTES = gv.attributes_for("2K26")
BADGES = gv.badges_for("2K26")


# --- Building an old-shaped database -----------------------------------------

def _old_schema_sql():
    """
    The `player` / `player_targets` / `user` shape as it was before step 2.

    Columns come from game_versions so this cannot drift from the real list;
    the point of the fixture is the SHAPE, not the names.
    """
    attribute_columns = ",\n    ".join(
        f'"{key}" INTEGER DEFAULT 25' for key in ATTRIBUTES)
    badge_columns = ",\n    ".join(
        f'"{key}" VARCHAR(20) DEFAULT \'None\'' for key in BADGES)

    return f"""
    CREATE TABLE user (
        id INTEGER NOT NULL PRIMARY KEY,
        username VARCHAR(150) NOT NULL UNIQUE,
        email VARCHAR(150) NOT NULL UNIQUE,
        password VARCHAR(150),
        is_active BOOLEAN
    );

    CREATE TABLE player (
        id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        user_id INTEGER NOT NULL REFERENCES user (id) ON DELETE CASCADE,
        devpoints INTEGER DEFAULT 0,
        badgepoints INTEGER DEFAULT 0,
        {attribute_columns},
        {badge_columns}
    );

    CREATE TABLE player_targets (
        id INTEGER NOT NULL PRIMARY KEY,
        player_id INTEGER NOT NULL REFERENCES player (id) ON DELETE CASCADE,
        {attribute_columns},
        {badge_columns}
    );
    """


@pytest.fixture
def old_database_path(tmp_path):
    """Where the throwaway old-shaped database lives, for tests that need the file."""
    return str(tmp_path / "old.db")


@pytest.fixture
def old_database(old_database_path):
    """
    A connection to an empty database in the pre-migration shape, with one
    user already in it. Transaction control is explicit, like the script's.
    """
    conn = sqlite3.connect(old_database_path)
    conn.isolation_level = None
    conn.executescript(_old_schema_sql())
    conn.execute(
        "INSERT INTO user (id, username, email, password, is_active) "
        "VALUES (1, 'tester', 'tester@example.com', 'x', 1)")
    yield conn
    conn.close()


def add_player(conn, player_id, name="Player", attributes=None, badges=None):
    """Insert one old-shaped player, defaulting every field the way the app did."""
    values = {key: 25 for key in ATTRIBUTES}
    values.update({key: "None" for key in BADGES})
    values.update(attributes or {})
    values.update(badges or {})
    columns = ["id", "name", "user_id"] + list(values)
    conn.execute(
        "INSERT INTO player ({}) VALUES ({})".format(
            ", ".join(f'"{c}"' for c in columns),
            ", ".join("?" * len(columns))),
        [player_id, name, 1] + list(values.values()))


def add_targets(conn, player_id, attributes=None, badges=None):
    """Insert one old-shaped player_targets row, defaulting to 25 / 'None'."""
    values = {key: 25 for key in ATTRIBUTES}
    values.update({key: "None" for key in BADGES})
    values.update(attributes or {})
    values.update(badges or {})
    columns = ["player_id"] + list(values)
    conn.execute(
        "INSERT INTO player_targets ({}) VALUES ({})".format(
            ", ".join(f'"{c}"' for c in columns),
            ", ".join("?" * len(columns))),
        [player_id] + list(values.values()))


def run_migration(conn):
    """Run the migration the way main() does: one transaction, then commit."""
    conn.execute("BEGIN")
    result = migrate_script.migrate(conn, gv)
    conn.execute("COMMIT")
    return result


def attributes_of(conn, player_id):
    return {key: (value, target) for key, value, target in conn.execute(
        "SELECT attribute_key, value, target_value FROM player_attribute "
        "WHERE player_id = ?", (player_id,))}


def badges_of(conn, player_id):
    return {key: (level, target) for key, level, target in conn.execute(
        "SELECT badge_key, level, target_level FROM player_badge "
        "WHERE player_id = ?", (player_id,))}


# --- The data actually moves -------------------------------------------------

def test_known_values_end_up_in_rows_exactly(old_database):
    """A player's attribute values arrive unchanged, one row per attribute."""
    add_player(old_database, 1, "Known",
               attributes={"agility": 91, "block": 47, "three_point_shot": 88})
    run_migration(old_database)

    rows = attributes_of(old_database, 1)
    assert len(rows) == len(ATTRIBUTES)
    assert rows["agility"][0] == 91
    assert rows["block"][0] == 47
    assert rows["three_point_shot"][0] == 88
    # Everything not named above kept the old default of 25.
    assert rows["hustle"][0] == 25


def test_known_badge_levels_end_up_in_rows_exactly(old_database):
    add_player(old_database, 1, "Badged",
               badges={"deadeye": "Gold", "dimer": "Hall of Fame"})
    run_migration(old_database)

    rows = badges_of(old_database, 1)
    assert len(rows) == len(BADGES)
    assert rows["deadeye"][0] == "Gold"
    assert rows["dimer"][0] == "Hall of Fame"


def test_badges_at_none_still_get_a_row(old_database):
    """We are not skipping empty badges - every badge of the version gets a row."""
    add_player(old_database, 1, "Empty")
    run_migration(old_database)

    rows = badges_of(old_database, 1)
    assert len(rows) == len(BADGES)
    assert all(level == "None" for level, _ in rows.values())


# --- The targets rule --------------------------------------------------------

def test_targets_are_carried_across_not_reset(old_database):
    """A real target survives the move."""
    add_player(old_database, 1)
    add_targets(old_database, 1,
                attributes={"agility": 95},
                badges={"deadeye": "Hall of Fame"})
    run_migration(old_database)

    assert attributes_of(old_database, 1)["agility"][1] == 95
    assert badges_of(old_database, 1)["deadeye"][1] == "Hall of Fame"


def test_a_target_left_at_the_old_default_is_copied_literally(old_database):
    """
    The decision from the handoff, pinned down.

    A player who has a targets row has been through the targets screen. A
    standing_dunk target of 25 on that row means "I never want this", so it is
    copied across as 25 - NOT promoted to the new default of 99. Same for a
    badge left at "None": it stays "None", it does not become "Legendary".
    """
    add_player(old_database, 1)
    add_targets(old_database, 1, attributes={"agility": 95})
    run_migration(old_database)

    attributes = attributes_of(old_database, 1)
    badges = badges_of(old_database, 1)
    assert attributes["agility"][1] == 95
    assert attributes["standing_dunk"][1] == 25, "must not be promoted to 99"
    assert badges["deadeye"][1] == "None", "must not be promoted to Legendary"


def test_player_with_no_targets_row_gets_the_new_defaults(old_database):
    """
    A player who never opened the targets screen expressed nothing, so it is
    safe to give them the new defaults: aim at 99 and Legendary.
    """
    add_player(old_database, 1, "No targets")
    run_migration(old_database)

    attributes = attributes_of(old_database, 1)
    badges = badges_of(old_database, 1)
    assert all(target == 99 for _, target in attributes.values())
    assert all(target == "Legendary" for _, target in badges.values())


def test_players_with_and_without_targets_in_the_same_run(old_database):
    """The two rules apply per player, not per database."""
    add_player(old_database, 1, "Has targets")
    add_player(old_database, 2, "No targets")
    add_targets(old_database, 1, attributes={"agility": 80})
    run_migration(old_database)

    assert attributes_of(old_database, 1)["agility"][1] == 80
    assert attributes_of(old_database, 1)["hustle"][1] == 25
    assert attributes_of(old_database, 2)["agility"][1] == 99
    assert badges_of(old_database, 2)["deadeye"][1] == "Legendary"


# --- Stamping, counts and nothing lost ---------------------------------------

def test_every_player_is_stamped_2k26(old_database):
    for player_id in range(1, 6):
        add_player(old_database, player_id, f"P{player_id}")
    run_migration(old_database)

    versions = [row[0] for row in old_database.execute(
        "SELECT game_version FROM player")]
    assert versions == ["2K26"] * 5


def test_row_counts_match_players_times_the_lists(old_database):
    for player_id in range(1, 8):
        add_player(old_database, player_id, f"P{player_id}")
    players, attribute_rows, badge_rows = run_migration(old_database)

    assert players == 7
    assert attribute_rows == 7 * len(ATTRIBUTES)
    assert badge_rows == 7 * len(BADGES)
    assert old_database.execute(
        "SELECT COUNT(*) FROM player_attribute").fetchone()[0] == 7 * 36
    assert old_database.execute(
        "SELECT COUNT(*) FROM player_badge").fetchone()[0] == 7 * 40


def test_nothing_is_lost(old_database):
    """No player disappears and no user disappears."""
    old_database.execute(
        "INSERT INTO user (id, username, email, password, is_active) "
        "VALUES (2, 'other', 'other@example.com', 'x', 1)")
    for player_id in range(1, 5):
        add_player(old_database, player_id, f"P{player_id}")

    before_players = old_database.execute(
        "SELECT id, name FROM player ORDER BY id").fetchall()
    before_users = old_database.execute(
        "SELECT id, username FROM user ORDER BY id").fetchall()

    run_migration(old_database)

    assert old_database.execute(
        "SELECT id, name FROM player ORDER BY id").fetchall() == before_players
    assert old_database.execute(
        "SELECT id, username FROM user ORDER BY id").fetchall() == before_users


def test_old_columns_are_left_alone(old_database):
    """Dropping them is a separate script - this one must not touch them."""
    add_player(old_database, 1, attributes={"agility": 77},
               badges={"deadeye": "Silver"})
    run_migration(old_database)

    row = old_database.execute(
        "SELECT agility, deadeye FROM player WHERE id = 1").fetchone()
    assert row == (77, "Silver")
    assert "player_targets" in migrate_script.table_names(old_database)


# --- Running it twice --------------------------------------------------------

def test_already_migrated_is_detected(old_database):
    add_player(old_database, 1)
    assert not migrate_script.already_migrated(old_database)
    run_migration(old_database)
    assert migrate_script.already_migrated(old_database)


def test_running_against_a_migrated_database_changes_nothing(
        old_database, old_database_path):
    """
    main() refuses on a second run, and the refusal costs nothing: the row
    counts and the data are identical afterwards.
    """
    add_player(old_database, 1, attributes={"agility": 64})
    run_migration(old_database)
    before = old_database.execute(
        "SELECT player_id, attribute_key, value, target_value "
        "FROM player_attribute ORDER BY id").fetchall()
    old_database.close()

    exit_code = migrate_script.main([old_database_path])
    assert exit_code == 1

    conn = sqlite3.connect(old_database_path)
    after = conn.execute(
        "SELECT player_id, attribute_key, value, target_value "
        "FROM player_attribute ORDER BY id").fetchall()
    conn.close()
    assert after == before


# --- The pre-flight ----------------------------------------------------------

def test_preflight_passes_on_clean_data(old_database):
    add_player(old_database, 1, attributes={"agility": 99, "block": 25})
    assert migrate_script.preflight(old_database, gv) == []


def test_preflight_catches_an_out_of_range_attribute(old_database):
    """The CHECK constraint would abort the bulk insert; this finds it first."""
    add_player(old_database, 1)
    old_database.execute("UPDATE player SET agility = 0 WHERE id = 1")

    problems = migrate_script.preflight(old_database, gv)
    assert any("player.agility" in line for line in problems)


def test_preflight_catches_a_null_attribute(old_database):
    add_player(old_database, 1)
    old_database.execute("UPDATE player SET block = NULL WHERE id = 1")

    problems = migrate_script.preflight(old_database, gv)
    assert any("player.block" in line for line in problems)


def test_preflight_catches_an_out_of_range_target(old_database):
    add_player(old_database, 1)
    add_targets(old_database, 1)
    old_database.execute("UPDATE player_targets SET agility = 120")

    problems = migrate_script.preflight(old_database, gv)
    assert any("player_targets.agility" in line for line in problems)


def test_preflight_catches_an_unknown_badge_level(old_database):
    add_player(old_database, 1)
    old_database.execute("UPDATE player SET deadeye = 'Platinum' WHERE id = 1")

    problems = migrate_script.preflight(old_database, gv)
    assert any("Platinum" in line for line in problems)


# --- Verification and rollback -----------------------------------------------

def test_verify_passes_after_a_good_migration(old_database):
    for player_id in range(1, 4):
        add_player(old_database, player_id, f"P{player_id}",
                   attributes={"agility": 60 + player_id})
    players, _, _ = run_migration(old_database)

    assert migrate_script.verify(old_database, gv, players) == []


def test_verify_notices_a_wrong_value(old_database):
    """If a copied value did not match its column, verify must say so."""
    add_player(old_database, 1, attributes={"agility": 60})
    players, _, _ = run_migration(old_database)
    old_database.execute(
        "UPDATE player_attribute SET value = 61 "
        "WHERE player_id = 1 AND attribute_key = 'agility'")

    problems = migrate_script.verify(old_database, gv, players)
    assert any("agility" in line for line in problems)


def test_verify_notices_a_missing_row(old_database):
    add_player(old_database, 1)
    players, _, _ = run_migration(old_database)
    old_database.execute(
        "DELETE FROM player_badge WHERE player_id = 1 AND badge_key = 'dimer'")

    problems = migrate_script.verify(old_database, gv, players)
    assert any("player_badge has" in line for line in problems)


def test_a_failure_mid_run_leaves_the_database_untouched(old_database):
    """
    The whole copy is one transaction. A player whose value the CHECK refuses
    aborts it, and nothing is left behind - no new tables, no new column.
    """
    add_player(old_database, 1)
    # Slip past the pre-flight by breaking the data after it would have run.
    old_database.execute("UPDATE player SET agility = 0 WHERE id = 1")

    old_database.execute("BEGIN")
    with pytest.raises(sqlite3.IntegrityError):
        migrate_script.migrate(old_database, gv)
    old_database.execute("ROLLBACK")

    assert not migrate_script.already_migrated(old_database)
    assert "game_version" not in migrate_script.column_names(
        old_database, "player")


# --- The backup --------------------------------------------------------------

def test_backup_is_written_and_readable(old_database, old_database_path, tmp_path):
    add_player(old_database, 1, "Backed up")

    out = migrate_script.backup_database(
        old_database_path, str(tmp_path / "backups"))

    assert os.path.exists(out)
    assert out.endswith(".bak"), "must not look like a live database"
    copy = sqlite3.connect(out)
    assert copy.execute("SELECT name FROM player").fetchone()[0] == "Backed up"
    copy.close()


def test_two_backups_of_the_same_database_do_not_collide(
        old_database, old_database_path, tmp_path):
    """
    The migration and the later drop script both back up the same file. Caught
    in rehearsal: with the same label they landed on the same name in the same
    second, and the second silently overwrote the first.
    """
    add_player(old_database, 1)
    directory = str(tmp_path / "backups")

    first = migrate_script.backup_database(
        old_database_path, directory, label="pre-migration")
    second = migrate_script.backup_database(
        old_database_path, directory, label="pre-drop")

    assert first != second
    assert os.path.exists(first)
    assert os.path.exists(second)


def test_a_backup_never_overwrites_a_backup(
        old_database, old_database_path, tmp_path):
    """Same label, same second - the second one gets a counter, not the axe."""
    add_player(old_database, 1)
    directory = str(tmp_path / "backups")

    paths = [migrate_script.backup_database(old_database_path, directory)
             for _ in range(3)]

    assert len(set(paths)) == 3
    assert all(os.path.exists(path) for path in paths)


# --- Schema drift guard ------------------------------------------------------

def test_script_ddl_still_matches_the_models():
    """
    The script writes its CREATE TABLE statements out by hand so that what runs
    against production is readable in the file. This test is the price of that:
    if the models change and the script does not, it fails here rather than in
    production.
    """
    from sqlalchemy.dialects import sqlite as sqlite_dialect
    from sqlalchemy.schema import CreateTable

    from app.models import PlayerAttribute, PlayerBadge

    def normalise(sql):
        return " ".join(sql.split()).rstrip(";")

    for model, script_ddl in (
        (PlayerAttribute, migrate_script.CREATE_PLAYER_ATTRIBUTE),
        (PlayerBadge, migrate_script.CREATE_PLAYER_BADGE),
    ):
        from_models = str(CreateTable(model.__table__).compile(
            dialect=sqlite_dialect.dialect()))
        assert normalise(from_models) == normalise(script_ddl), (
            f"{model.__tablename__} DDL in "
            f"scripts/migrate_to_game_versions.py no longer matches "
            f"app/models.py"
        )


def test_migrated_schema_accepts_the_orm_constraints(old_database):
    """
    The tables the script creates really do carry the constraints, not just the
    column names: a value outside 25-99 is refused by the database itself.
    """
    add_player(old_database, 1)
    run_migration(old_database)

    with pytest.raises(sqlite3.IntegrityError):
        old_database.execute(
            "INSERT INTO player_attribute "
            "(player_id, attribute_key, value, target_value) "
            "VALUES (1, 'made_up', 5, 99)")

    with pytest.raises(sqlite3.IntegrityError):
        old_database.execute(
            "INSERT INTO player_attribute "
            "(player_id, attribute_key, value, target_value) "
            "VALUES (1, 'agility', 50, 99)")
