# Browseterm DB
SQLAlchemy ORM library setup. Handles migrations as well.

## P15 - `container_snapshots`

Adds `container_snapshots` (one row per workspace save/snapshot attempt - `SnapshotOps` in
`browseterm_db/operations/snapshot_ops.py`, model in `browseterm_db/models/container_snapshots.py`)
and `containers.next_snapshot_sequence` (the atomic version-allocation counter P16 will use).
Deliberately a separate table from `images` (the base-image catalog) - saved workspace images
never mix into that. `container_snapshots.container_id` has a **DB-level** `ON DELETE CASCADE`,
not just an ORM-level one - `ContainerOps.delete()` does a bulk `query.delete()` that bypasses
SQLAlchemy ORM cascades entirely, so this has to be enforced by Postgres itself. See
`~/browseterm/p.md`'s "P15" section for the full write-up, including the version-formatting
(`browseterm_db/common/snapshot_version.py`, "do NOT perform version arithmetic using strings").

# PreRequisites
1. Python - 3.11
   To install on a mac. First download and install `python3.11`:
   ```bash
   $ brew install python@3.11
   ```
   Once installed get the path of python3.11:
   ```bash
   $ which python3.11
   ```
   Note this path down.

2. Poetry
   To install poetry on a mac.
   ```bash
   $ brew install poetry
   ```

# Setting up
- To use this library simply install it.
   ```bash
   $ poetry add git+https://github.com/Zim95/browseterm-db.git#main
   ```
- You can also contribute to the library by cloning the repository.
   ```bash
   $ git clone https://github.com/Zim95/browseterm-db.git
   ```

# Running tests
- To run the tests, we need to first clone the repository:
   ```bash
   $ git clone https://github.com/Zim95/browseterm-db.git
   ```

- Create an `.env` file at the root of the directory with the following values:
   ```text
   DB_USERNAME=<username>
   DB_PASSWORD=<password>
   DB_HOST=<host>
   DB_PORT=<port>
   DB_DATABASE=<db_name>
   TEST_DB_USERNAME=<username>
   TEST_DB_PASSWORD=<password>
   TEST_DB_HOST=<host>
   TEST_DB_PORT=<port>
   TEST_DB_DATABASE=<test_db_name>
   ```
   Make sure a database with this connection configuration exists. Do not use quotations in the values. Do not add spaces around =.

   > Note: Only the `DB_*` variables are needed for migrations and seeding (`init.py` / `upgrade.py`). The `TEST_DB_*` variables are used **only** for running the test suite.
   >
   > `DB_HOST=localhost` works when you port-forward the Postgres service: `kubectl port-forward service/browseterm-pg-service -n browseterm 5432:5432`.

- To run all the tests:
   ```bash
   $ python -m unittest discover -s ./tests/ -p "test_*.py"
   ```
   > Each file's own `AAA_InitialSetup` test does a **destructive** `reset_database()` +
   > fresh-autogenerate-from-current-models before its own tests run. This has a real, observed
   > fragility running many files back-to-back against the same long-lived TEST_DB via `discover`
   > (confirmed pre-existing this session while verifying P15's own new test file, unrelated to
   > any specific model - reproducible on a clean checkout with zero P15 changes present too) -
   > likely stale Postgres ENUM types not fully cleaned up between resets. **Running each test
   > file individually (see below) is the reliable way to verify a change**, not `discover` across
   > everything in one process. Never point `TEST_DB_*` at a real/shared database given the
   > destructive resets - always a disposable, single-purpose Postgres instance.

- To run individual file tests:
   ```bash
   $ python -m unittest ./tests/<test_file>.py
   ```

- To run a specific test within the file:
   ```bash
   $ python -m unittest tests.<test_file_without_py_extension>.<classname>.<test_method_name>
   ```
   DO NOT DO THIS: The tests require setup. Running them individually will fail.


# Working with Migrations
- If this is your first time setting up browsetermdb. Run the `init.py` file.
   ```bash
   $ python init.py
   ```
   > ⚠️ **DESTRUCTIVE — FIRST-TIME SETUP ONLY.** `init.py` **drops all existing tables and enums**, then creates the initial migration, upgrades the database, AND seeds `subscription_types` + `images`. Run this only on a fresh/empty database. For an **existing** database, DO NOT run `init.py` — use the non-destructive `python upgrade.py upgrade` instead.

- If you want to create and apply the migration.
   ```bash
   $ python upgrade.py <message>
   ```

- If you want to only create the migration file without applying.
   ```bash
   $ python upgrade.py create <message>
   ```
   Make the edits in your migration file, then hit:
   ```bash
   $ python upgrade.py upgrade
   ```

# Setting up the Database
1. Clone this repository.
2. Install the virtual environment and activate it.
3. Then hit upgrade:
   ```bash
   $ python upgrade.py upgrade
   ```
   This will create all your models and apply all the existing migrations that we have.

4. Then call state manager to maintain state.
   ```bash
   $ python db_state_manager/state_manager.py
   ```
   > Note: `init.py` already runs the seeding step, so if you set up via `init.py` this call is optional (it is idempotent).
