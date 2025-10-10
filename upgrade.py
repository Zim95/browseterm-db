'''
Here we setup initial migrations for the project.
'''

# builtins
from dotenv import load_dotenv
import os
import sys

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import MIGRATIONS_DIR

# load the environment variables
load_dotenv('.env')


class UpgradeMigrations():
    '''
    Setup the initial migrations.
    '''
    def __init__(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('DB_USERNAME'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_DATABASE')
        )
        self.migrator: Migrator = Migrator(self.db_config, MIGRATIONS_DIR)

    def upgrade(self, message: str) -> None:
        '''
        Setup the initial migrations.
        '''
        # create all tables
        self.migrator.revision(message)
        # upgrade the database
        self.migrator.upgrade()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python upgrade.py <message>")
        sys.exit(1)
    upgrade_migrations = UpgradeMigrations()
    upgrade_migrations.upgrade(sys.argv[1])
