# Browseterm DB
SQLAlchemy ORM library setup. Handles migrations as well.

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
   $ https://github.com/Zim95/browseterm-db.git
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

- To run all the tests:
   ```bash
   $ python -m unittest discover -s ./tests/ -p "test_*.py"
   ```

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
