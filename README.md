# Browseterm DB
SQLAlchemy ORM library setup. Handles migrations as well.

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
