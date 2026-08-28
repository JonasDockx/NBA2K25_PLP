"""
Move every player's attributes and badges out of the wide `player` table and
into the `player_attribute` / `player_badge` row tables, and stamp every
existing player as "2K26".

Step 3 of 6 for Game Version support. Run once, on the server, at step 6.

This is deliberately a plain script and not an Alembic migration: it happens
exactly once, and it needs to be readable top to bottom by a human who is
about to run it on live data. It talks to SQLite directly and never imports
the Flask app, so it cannot accidentally pick up a different database than the
one named on the command line.

WHAT IT DOES NOT DO: it does not drop the old columns. They stay exactly where
they are, ignored by the app, as a free rollback. Dropping them is a separate
script - scripts/drop_old_player_columns.py - run days later, once the site has
been proven on the new shape.

Usage:

    python scripts/migrate_to_game_versions.py instance/nba2k25.db

Add --backup-dir to put the safety copy somewhere other than next to the
database. There is no flag to skip the backup, on purpose.
"""

import argparse
import datetime
import importlib.util
import os
import sqlite3
import sys

# --- Loading the game version definitions ------------------------------------

# app/game_versions.py is loaded straight off disk rather than with
# `from app.game_versions import ...`, because a normal import would run
# app/__init__.py, which builds the Flask app, reads .env and opens a mail
# connection. None of that has any business running inside a migration.
# The lists still come from the one real source; they are never retyped here.


def load_game_versions(repo_root):
    """Import app/game_versions.py on its own, without starting Flask."""
    path = os.path.join(repo_root, "app", "game_versions.py")
    if not os.path.exists(path):
        raise SystemExit(f"Cannot find {path}. Run this from the repo root.")
    spec = importlib.util.spec_from_file_location("_game_versions", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- The schema this script creates ------------------------------------------

# Written out rather than generated from the models, so that what runs against
# production is visible in this file. tests/test_migration.py asserts that it
# still matches what db.create_all() produces - if the models change and this
# does not, that test fails.
#
# One deliberate difference from the models: game_version is added with a
# server-side DEFAULT '2K26'. SQLite requires a non-null default to add a
# NOT NULL column to a table that already has rows, and that default is what
# stamps every existing player in a single statement. A database built fresh by
# db.create_all() has no such default; there, the ORM always supplies the value.

CREATE_PLAYER_ATTRIBUTE = """
CREATE TABLE player_attribute (
	id INTEGER NOT NULL,
	player_id INTEGER NOT NULL,
	attribute_key VARCHAR(50) NOT NULL,
	value INTEGER NOT NULL,
	target_value INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_player_attribute_key UNIQUE (player_id, attribute_key),
	CONSTRAINT ck_player_attribute_value_range CHECK (value BETWEEN 25 AND 99),
	CONSTRAINT ck_player_attribute_target_range CHECK (target_value BETWEEN 25 AND 99),
	FOREIGN KEY(player_id) REFERENCES player (id) ON DELETE CASCADE
)
"""

CREATE_PLAYER_BADGE = """
CREATE TABLE player_badge (
	id INTEGER NOT NULL,
	player_id INTEGER NOT NULL,
	badge_key VARCHAR(50) NOT NULL,
	level VARCHAR(20) NOT NULL,
	target_level VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_player_badge_key UNIQUE (player_id, badge_key),
	FOREIGN KEY(player_id) REFERENCES player (id) ON DELETE CASCADE
)
"""

ADD_GAME_VERSION = (
    "ALTER TABLE player ADD COLUMN game_version VARCHAR(10) "
    "NOT NULL DEFAULT '2K26'"
)


# --- Small helpers -----------------------------------------------------------

def table_names(conn):
    """Every table in the database, as a set of names."""
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in rows}


def column_names(conn, table):
    """Every column of `table`, as a set of names."""
    rows = conn.execute(f'PRAGMA table_info("{table}")')
    return {row[1] for row in rows}


def already_migrated(conn):
    """
    True if this database has been through the migration already.

    Checked by looking for the new tables, not by a version marker, because a
    version marker can be written when the data was not.
    """
    return {"player_attribute", "player_badge"} <= table_names(conn)


# --- Step 1: the backup ------------------------------------------------------

def backup_database(db_path, backup_dir=None, label="pre-migration"):
    """
    Take a timestamped copy of the database and prove it is readable.

    Uses SQLite's own backup, not a file copy, for the same reason the nightly
    job does: a plain copy can catch the file mid-write and produce something
    that only looks fine. Returns the path written.

    The copy is named .bak rather than .db so it can never be mistaken for a
    live database, and does not match the nightly job's nba2k25_*.db.gz pattern.

    `label` says which script made it, so the migration's backup and the later
    drop script's backup cannot land on the same name. A counter is added if
    the name is somehow still taken - a backup must never overwrite a backup.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = backup_dir or os.path.dirname(os.path.abspath(db_path))
    os.makedirs(directory, exist_ok=True)
    base = os.path.basename(db_path) + f".{label}-{stamp}"
    out = os.path.join(directory, base + ".bak")
    counter = 2
    while os.path.exists(out):
        out = os.path.join(directory, f"{base}-{counter}.bak")
        counter += 1

    source = sqlite3.connect(db_path)
    target = sqlite3.connect(out)
    try:
        with target:
            source.backup(target)
    finally:
        target.close()
        source.close()

    check = sqlite3.connect(out)
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        players = check.execute("SELECT COUNT(*) FROM player").fetchone()[0]
    finally:
        check.close()

    if not ok:
        raise SystemExit(f"Backup at {out} failed its integrity check. Stopping.")

    print(f"  backup written : {out}")
    print(f"  it contains    : {players} players, {os.path.getsize(out)} bytes")
    return out


# --- Step 2: the pre-flight --------------------------------------------------

def preflight(conn, gv):
    """
    Look for data the new tables would refuse, before anything is written.

    player_attribute carries real CHECK constraints on value and target_value.
    A single row out of range aborts the bulk insert halfway through. Better to
    find that now than during the run, so this reports every problem at once
    rather than dying on the first one.

    Returns a list of human-readable problem strings; empty means good to go.
    """
    problems = []
    attributes = gv.attributes_for(gv.DEFAULT_GAME_VERSION)
    badges = gv.badges_for(gv.DEFAULT_GAME_VERSION)
    lo, hi = gv.MIN_ATTRIBUTE_VALUE, gv.MAX_ATTRIBUTE_VALUE
    tables = table_names(conn)

    for table in ("player", "player_targets"):
        if table not in tables:
            continue
        columns = column_names(conn, table)

        for key in attributes:
            if key not in columns:
                problems.append(f"{table}.{key} is missing")
                continue
            n = conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{key}" IS NULL '
                f'OR "{key}" NOT BETWEEN ? AND ?', (lo, hi)).fetchone()[0]
            if n:
                problems.append(
                    f"{table}.{key}: {n} row(s) NULL or outside {lo}-{hi}")

        placeholders = ",".join("?" * len(gv.BADGE_LEVELS))
        for key in badges:
            if key not in columns:
                problems.append(f"{table}.{key} is missing")
                continue
            rows = conn.execute(
                f'SELECT DISTINCT "{key}" FROM "{table}" WHERE "{key}" IS NULL '
                f'OR "{key}" NOT IN ({placeholders})', gv.BADGE_LEVELS).fetchall()
            for (value,) in rows:
                problems.append(f"{table}.{key}: unknown badge level {value!r}")

    return problems


# --- Steps 3 to 5: the migration itself --------------------------------------

def migrate(conn, gv, progress=None):
    """
    Create the new shape and copy every player's data into it.

    Does NOT commit and does NOT open a transaction - the caller owns both, so
    that a failed verification can roll the whole thing back. This is the piece
    the tests drive directly.

    Returns (players, attribute_rows_written, badge_rows_written).
    """
    version = gv.DEFAULT_GAME_VERSION
    attributes = gv.attributes_for(version)
    badges = gv.badges_for(version)

    # The two new tables, and the new column. Adding game_version with a
    # DEFAULT also stamps every existing row "2K26" in one statement.
    # See docs/adr/0003-existing-players-stamped-2k26.md.
    conn.execute(CREATE_PLAYER_ATTRIBUTE)
    conn.execute(CREATE_PLAYER_BADGE)
    if "game_version" not in column_names(conn, "player"):
        conn.execute(ADD_GAME_VERSION)
    else:
        conn.execute("UPDATE player SET game_version = ?", (version,))

    # Copying the data across.
    #
    # THE TARGETS RULE, decided against the real data - do not change casually.
    # 57 of 3228 production players have a player_targets row, and every one of
    # those was filled in deliberately. So a targets row is copied across
    # EXACTLY as it stands, including values left at 25 and badges left at
    # "None": on a guard, a standing_dunk target of 25 means "I never want
    # this", not "nobody got round to it". Rewriting those to 99 would invent
    # an ambition the user never expressed.
    #
    # A player with NO targets row expressed nothing at all, so it gets the new
    # defaults instead: 99 for attributes, "Legendary" for badges.
    default_target_value = gv.DEFAULT_TARGET_ATTRIBUTE_VALUE
    default_target_level = gv.DEFAULT_TARGET_BADGE_LEVEL

    targets = {}
    if "player_targets" in table_names(conn):
        target_columns = ["player_id"] + attributes + badges
        select_targets = "SELECT {} FROM player_targets".format(
            ", ".join(f'"{c}"' for c in target_columns))
        for row in conn.execute(select_targets):
            targets[row[0]] = dict(zip(target_columns[1:], row[1:]))

    player_columns = ["id"] + attributes + badges
    select_players = "SELECT {} FROM player ORDER BY id".format(
        ", ".join(f'"{c}"' for c in player_columns))

    attribute_rows = []
    badge_rows = []
    players = 0

    for row in conn.execute(select_players).fetchall():
        player_id = row[0]
        current = dict(zip(player_columns[1:], row[1:]))
        target = targets.get(player_id)
        players += 1

        for key in attributes:
            target_value = (
                target[key] if target is not None else default_target_value)
            attribute_rows.append((player_id, key, current[key], target_value))

        for key in badges:
            target_level = (
                target[key] if target is not None else default_target_level)
            badge_rows.append((player_id, key, current[key], target_level))

        if progress and players % 500 == 0:
            progress(players)

    conn.executemany(
        "INSERT INTO player_attribute "
        "(player_id, attribute_key, value, target_value) VALUES (?, ?, ?, ?)",
        attribute_rows)
    conn.executemany(
        "INSERT INTO player_badge "
        "(player_id, badge_key, level, target_level) VALUES (?, ?, ?, ?)",
        badge_rows)

    return players, len(attribute_rows), len(badge_rows)


# --- Step 6: verification ----------------------------------------------------

def verify(conn, gv, players):
    """
    Prove the copy is right before anything is committed.

    Two kinds of check: the row counts are exactly what they should be, and a
    spread of players is read back and compared field by field against the old
    columns it came from. Returns a list of problems; empty means good.
    """
    problems = []
    version = gv.DEFAULT_GAME_VERSION
    attributes = gv.attributes_for(version)
    badges = gv.badges_for(version)

    expected_attributes = players * len(attributes)
    expected_badges = players * len(badges)
    actual_attributes = conn.execute(
        "SELECT COUNT(*) FROM player_attribute").fetchone()[0]
    actual_badges = conn.execute(
        "SELECT COUNT(*) FROM player_badge").fetchone()[0]

    if actual_attributes != expected_attributes:
        problems.append(
            f"player_attribute has {actual_attributes} rows, expected "
            f"{players} players x {len(attributes)} = {expected_attributes}")
    if actual_badges != expected_badges:
        problems.append(
            f"player_badge has {actual_badges} rows, expected "
            f"{players} players x {len(badges)} = {expected_badges}")

    unstamped = conn.execute(
        "SELECT COUNT(*) FROM player WHERE game_version IS NOT ?",
        (version,)).fetchone()[0]
    if unstamped:
        problems.append(f"{unstamped} player(s) not stamped {version}")

    orphans = conn.execute(
        "SELECT COUNT(*) FROM player_attribute a WHERE NOT EXISTS "
        "(SELECT 1 FROM player p WHERE p.id = a.player_id)").fetchone()[0]
    if orphans:
        problems.append(f"{orphans} player_attribute row(s) point at no player")

    # Read a spread of players back and compare every field against the column
    # it was copied from. Every 97th id, so the sample is not just the first
    # few, plus the lowest and highest ids.
    sample = [row[0] for row in conn.execute(
        "SELECT id FROM player WHERE id % 97 = 0 "
        "OR id = (SELECT MIN(id) FROM player) "
        "OR id = (SELECT MAX(id) FROM player)").fetchall()]

    select_old = "SELECT {} FROM player WHERE id = ?".format(
        ", ".join(f'"{c}"' for c in attributes + badges))

    for player_id in sample:
        old = conn.execute(select_old, (player_id,)).fetchone()
        old_values = dict(zip(attributes + badges, old))

        new_attributes = dict(conn.execute(
            "SELECT attribute_key, value FROM player_attribute "
            "WHERE player_id = ?", (player_id,)).fetchall())
        new_badges = dict(conn.execute(
            "SELECT badge_key, level FROM player_badge "
            "WHERE player_id = ?", (player_id,)).fetchall())

        for key in attributes:
            if new_attributes.get(key) != old_values[key]:
                problems.append(
                    f"player {player_id} {key}: row says "
                    f"{new_attributes.get(key)!r}, "
                    f"column says {old_values[key]!r}")
        for key in badges:
            if new_badges.get(key) != old_values[key]:
                problems.append(
                    f"player {player_id} {key}: row says "
                    f"{new_badges.get(key)!r}, "
                    f"column says {old_values[key]!r}")

    if not problems:
        print(f"  verified       : {len(sample)} players re-read "
              f"field by field, all match")
    return problems


# --- Putting it together -----------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move players onto the Game Version row tables.")
    parser.add_argument("database", help="path to nba2k25.db")
    parser.add_argument(
        "--backup-dir", default=None,
        help="where to put the safety copy (default: next to the database)")
    parser.add_argument(
        "--repo-root", default=None,
        help="repo root holding app/game_versions.py "
             "(default: the parent of scripts/)")
    args = parser.parse_args(argv)

    repo_root = args.repo_root or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    gv = load_game_versions(repo_root)

    if not os.path.exists(args.database):
        raise SystemExit(f"No such database: {args.database}")

    conn = sqlite3.connect(args.database)
    # Explicit transaction control: nothing is committed until verification
    # has passed.
    conn.isolation_level = None

    try:
        if already_migrated(conn):
            attribute_rows = conn.execute(
                "SELECT COUNT(*) FROM player_attribute").fetchone()[0]
            badge_rows = conn.execute(
                "SELECT COUNT(*) FROM player_badge").fetchone()[0]
            print()
            print("This database has already been migrated.")
            print(f"  player_attribute: {attribute_rows} rows")
            print(f"  player_badge:     {badge_rows} rows")
            print("Refusing to run again. Nothing changed.")
            return 1

        players = conn.execute("SELECT COUNT(*) FROM player").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM user").fetchone()[0]
        if "player_targets" in table_names(conn):
            with_targets = conn.execute(
                "SELECT COUNT(*) FROM player p WHERE EXISTS "
                "(SELECT 1 FROM player_targets t WHERE t.player_id = p.id)"
            ).fetchone()[0]
        else:
            with_targets = 0

        version = gv.DEFAULT_GAME_VERSION
        n_attributes = len(gv.attributes_for(version))
        n_badges = len(gv.badges_for(version))

        print()
        print("About to migrate:", os.path.abspath(args.database))
        print(f"  sqlite version : {sqlite3.sqlite_version}")
        print(f"  users          : {users}")
        print(f"  players        : {players}")
        print(f"    {with_targets} have a targets row - copied across as-is")
        print(f"    {players - with_targets} do not - given defaults "
              f"{gv.DEFAULT_TARGET_ATTRIBUTE_VALUE} / "
              f"{gv.DEFAULT_TARGET_BADGE_LEVEL}")
        print(f"  will create    : {players * n_attributes} "
              f"player_attribute rows")
        print(f"                   {players * n_badges} player_badge rows")
        print(f"  every player stamped: {version}")
        print()
        print("The old columns are NOT dropped. That is a separate script, later.")
        print()

        print("Step 1 of 4 - safety backup")
        backup_database(args.database, args.backup_dir)
        print()

        print("Step 2 of 4 - pre-flight checks")
        problems = preflight(conn, gv)
        if problems:
            print(f"  FOUND {len(problems)} problem(s) that would break "
                  f"the migration:")
            for line in problems[:20]:
                print("    -", line)
            if len(problems) > 20:
                print(f"    ... and {len(problems) - 20} more")
            print()
            print("Nothing has been changed. Fix these first.")
            return 2
        print("  no out-of-range values, no unknown badge levels")
        print()

        answer = input('Type "migrate" to go ahead, anything else to stop: ')
        if answer.strip() != "migrate":
            print("Stopped. Nothing changed.")
            return 1
        print()

        print("Step 3 of 4 - copying")
        conn.execute("BEGIN")
        try:
            counted, attribute_rows, badge_rows = migrate(
                conn, gv, progress=lambda n: print(f"  {n} players..."))
            print(f"  {counted} players, {attribute_rows} attribute rows, "
                  f"{badge_rows} badge rows")
            print()

            print("Step 4 of 4 - verifying before commit")
            problems = verify(conn, gv, counted)
            if problems:
                conn.execute("ROLLBACK")
                print(f"  VERIFICATION FAILED - {len(problems)} problem(s):")
                for line in problems[:20]:
                    print("    -", line)
                print()
                print("Rolled back. The database is exactly as it was.")
                return 3
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            print()
            print("Something went wrong. Rolled back; the database is unchanged.")
            raise

        print()
        print("Done. The database is migrated.")
        print("The old columns are still there. Drop them later with")
        print("scripts/drop_old_player_columns.py, once the site is proven.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
