"""
Drop the old wide columns from `player`, and drop `player_targets` entirely.

The second half of step 3, deliberately kept as its own script and run DAYS
AFTER scripts/migrate_to_game_versions.py - not in the same sitting.

Why split it: the data copy and the schema surgery are the two risky operations,
and splitting them means they can never fail in the same run. In between, the
old columns sit there ignored by the app, which makes them a free rollback: if
anything about the new shape turns out to be wrong, the original data is still
right there in the same database.

DO NOT RUN THIS until the site has been running on the new shape for a few days
and you are happy with it. Once the columns are gone, the only way back is a
backup.

Usage:

    python scripts/drop_old_player_columns.py instance/nba2k25.db

SQLite gained ALTER TABLE DROP COLUMN in 3.35. THE SERVER DOES NOT HAVE IT:
it runs Ubuntu 20.04 with SQLite 3.31.1, checked 28 Aug 2026. So in production
this script takes the other path - create a new table, copy the rows over, drop
the old one, rename - which works on any version. It picks the path itself and
prints which one before doing anything.

Both paths have been rehearsed on a real production copy: the rebuild on an
actual 3.31.1 (Ubuntu 20.04 under WSL, same as the server) and the in-place
drop on 3.50.4. --force-rebuild takes the rebuild path even where DROP COLUMN
is available, which is how the tests cover it on a modern laptop.
"""

import argparse
import os
import sqlite3
import sys

# The migration script next door already knows how to load game_versions
# without starting Flask, how to take a backup, and how to look at the schema.
# Reusing it keeps the two scripts honest with each other.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrate_to_game_versions import (  # noqa: E402
    already_migrated,
    backup_database,
    column_names,
    load_game_versions,
    table_names,
)

DROP_COLUMN_MIN_VERSION = (3, 35, 0)


def supports_drop_column():
    """True if this SQLite can do ALTER TABLE ... DROP COLUMN."""
    version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    return version >= DROP_COLUMN_MIN_VERSION


def columns_to_drop(conn, gv):
    """
    Which columns of `player` are the old per-attribute and per-badge ones.

    Worked out by intersecting the real table with the key lists in
    game_versions, so nothing is retyped and a column that is not actually
    there is simply not in the answer. Every badge name from every version is
    considered, not just 2K26's, so a column can never be left behind.
    """
    present = column_names(conn, "player")
    keys = set(gv.ATTRIBUTE_NAMES) | set(gv.BADGE_NAMES)
    return sorted(present & keys)


def check_safe_to_drop(conn, gv):
    """
    Refuse unless the data is provably already somewhere else.

    Dropping is irreversible, so nothing goes until every player provably has
    a full set of attribute and badge rows and a game_version.

    Returns a list of problems; empty means safe.
    """
    problems = []

    if not already_migrated(conn):
        return ["This database has not been migrated yet. "
                "Run scripts/migrate_to_game_versions.py first."]

    version = gv.DEFAULT_GAME_VERSION
    attributes = gv.attributes_for(version)
    badges = gv.badges_for(version)

    players = conn.execute("SELECT COUNT(*) FROM player").fetchone()[0]
    attribute_rows = conn.execute(
        "SELECT COUNT(*) FROM player_attribute").fetchone()[0]
    badge_rows = conn.execute("SELECT COUNT(*) FROM player_badge").fetchone()[0]

    if attribute_rows != players * len(attributes):
        problems.append(
            f"player_attribute has {attribute_rows} rows, expected "
            f"{players} x {len(attributes)} = {players * len(attributes)}")
    if badge_rows != players * len(badges):
        problems.append(
            f"player_badge has {badge_rows} rows, expected "
            f"{players} x {len(badges)} = {players * len(badges)}")

    missing = conn.execute(
        "SELECT COUNT(*) FROM player p WHERE NOT EXISTS "
        "(SELECT 1 FROM player_attribute a WHERE a.player_id = p.id)"
    ).fetchone()[0]
    if missing:
        problems.append(f"{missing} player(s) have no attribute rows at all")

    # Deliberately NOT comparing the rows against the old columns. By now the
    # app has been running on the new shape for days and writing to the rows,
    # so the two disagreeing is expected and correct - the rows are the truth
    # and the columns are the stale copy. What matters is that no row is
    # MISSING, which the counts above catch.
    unstamped = conn.execute(
        "SELECT COUNT(*) FROM player WHERE game_version IS NULL "
        "OR game_version = ''").fetchone()[0]
    if unstamped:
        problems.append(f"{unstamped} player(s) have no game_version")

    return problems


def drop_columns_in_place(conn, columns, progress=None):
    """The easy path: ALTER TABLE ... DROP COLUMN, one at a time."""
    for index, column in enumerate(columns, 1):
        conn.execute(f'ALTER TABLE player DROP COLUMN "{column}"')
        if progress and index % 20 == 0:
            progress(index, len(columns))


def rebuild_player_table(conn, columns_to_remove):
    """
    The old path, for SQLite before 3.35: create / copy / drop / rename.

    Follows the procedure in the SQLite docs. The caller must have turned
    foreign keys off BEFORE opening the transaction - the pragma is a no-op
    inside one.

    The SQLite docs suggest PRAGMA legacy_alter_table=ON around the final
    rename, so that RENAME TO does not go rewriting REFERENCES clauses in other
    tables. It is not set here because it is not needed: nothing references
    "player_new", so there is nothing for the rename to rewrite. Checked on the
    server's own 3.31.1 against a production copy - player_attribute and
    player_badge still say REFERENCES player, foreign_key_check is clean, and
    ON DELETE CASCADE still fires.
    """
    keep = []
    for _, name, decl_type, notnull, default, pk in conn.execute(
            "PRAGMA table_info(player)"):
        if name in columns_to_remove:
            continue
        piece = f'"{name}" {decl_type}'
        if pk:
            piece += " NOT NULL PRIMARY KEY"
        else:
            if notnull:
                piece += " NOT NULL"
            if default is not None:
                piece += f" DEFAULT {default}"
        keep.append((name, piece))

    names = [name for name, _ in keep]
    definitions = ",\n    ".join(piece for _, piece in keep)

    conn.execute(f"""
        CREATE TABLE player_new (
            {definitions},
            FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
        )
    """)
    column_list = ", ".join(f'"{name}"' for name in names)
    conn.execute(
        f"INSERT INTO player_new ({column_list}) SELECT {column_list} FROM player")
    conn.execute("DROP TABLE player")
    conn.execute("ALTER TABLE player_new RENAME TO player")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Drop the old wide columns from player, days after the migration.")
    parser.add_argument("database", help="path to nba2k25.db")
    parser.add_argument("--backup-dir", default=None,
                        help="where to put the safety copy")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--force-rebuild", action="store_true",
                        help="take the create/copy/rename path even where "
                             "DROP COLUMN is available (used by the tests)")
    args = parser.parse_args(argv)

    repo_root = args.repo_root or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    gv = load_game_versions(repo_root)

    if not os.path.exists(args.database):
        raise SystemExit(f"No such database: {args.database}")

    conn = sqlite3.connect(args.database)
    conn.isolation_level = None

    try:
        columns = columns_to_drop(conn, gv)
        has_targets = "player_targets" in table_names(conn)

        if not columns and not has_targets:
            print()
            print("Nothing to do - the old columns are already gone and there "
                  "is no player_targets table.")
            return 1

        players = conn.execute("SELECT COUNT(*) FROM player").fetchone()[0]
        rebuild = args.force_rebuild or not supports_drop_column()

        print()
        print("About to drop old columns from:", os.path.abspath(args.database))
        print(f"  sqlite version : {sqlite3.sqlite_version}")
        print(f"  players        : {players}")
        print(f"  columns to drop: {len(columns)}")
        print(f"  drop player_targets: {'yes' if has_targets else 'already gone'}")
        print(f"  method         : "
              f"{'rebuild the table (create/copy/rename)' if rebuild else 'ALTER TABLE DROP COLUMN'}")
        if not args.force_rebuild and rebuild:
            print(f"                   (this SQLite is older than "
                  f"{'.'.join(str(n) for n in DROP_COLUMN_MIN_VERSION)})")
        print()
        print("THIS IS IRREVERSIBLE. After this the old data exists only in backups.")
        print()

        print("Step 1 of 4 - safety checks")
        problems = check_safe_to_drop(conn, gv)
        if problems:
            print(f"  REFUSING - {len(problems)} problem(s):")
            for line in problems:
                print("    -", line)
            print()
            print("Nothing has been changed.")
            return 2
        print("  every player has a full set of attribute and badge rows")
        print("  every player has a game_version")
        print()

        print("Step 2 of 4 - safety backup")
        backup_database(args.database, args.backup_dir, label="pre-drop")
        print()

        answer = input('Type "drop" to go ahead, anything else to stop: ')
        if answer.strip() != "drop":
            print("Stopped. Nothing changed.")
            return 1
        print()

        print("Step 3 of 4 - dropping")
        # Must be set outside the transaction to have any effect.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")
        try:
            if rebuild:
                rebuild_player_table(conn, set(columns))
                print("  player table rebuilt without the old columns")
            else:
                drop_columns_in_place(
                    conn, columns,
                    progress=lambda i, n: print(f"  dropped {i} of {n}..."))
                print(f"  dropped {len(columns)} columns")

            if has_targets:
                conn.execute("DROP TABLE player_targets")
                print("  dropped player_targets")

            print()
            print("Step 4 of 4 - verifying before commit")
            left = columns_to_drop(conn, gv)
            broken = conn.execute("PRAGMA foreign_key_check").fetchall()
            after = conn.execute("SELECT COUNT(*) FROM player").fetchone()[0]

            trouble = []
            if left:
                trouble.append(f"{len(left)} old column(s) still there: {left[:5]}")
            if broken:
                trouble.append(f"{len(broken)} broken foreign key reference(s)")
            if after != players:
                trouble.append(f"player count changed: {players} -> {after}")
            if "player_targets" in table_names(conn):
                trouble.append("player_targets is still there")

            if trouble:
                conn.execute("ROLLBACK")
                print("  VERIFICATION FAILED:")
                for line in trouble:
                    print("    -", line)
                print()
                print("Rolled back. The database is exactly as it was.")
                return 3

            print(f"  {after} players still here, no broken references, "
                  f"no old columns left")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            print()
            print("Something went wrong. Rolled back; the database is unchanged.")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

        # VACUUM has to happen outside a transaction. It reclaims the space the
        # dropped columns were using, which is most of the file.
        before_size = os.path.getsize(args.database)
        conn.execute("VACUUM")
        after_size = os.path.getsize(args.database)

        print()
        print(f"Done. Database went from {before_size} to {after_size} bytes.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
