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
