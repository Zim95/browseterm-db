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
        Create a new migration and apply it.
        '''
        # create all tables
        self.migrator.revision(message)
        # upgrade the database
        self.migrator.upgrade()

    def create_migration(self, message: str) -> None:
        '''
        Create a new migration file without applying it.
        '''
        self.migrator.revision(message, autogenerate=True)

    def upgrade_head(self) -> None:
        '''
        Upgrade to the latest migration (head) without creating a new migration.
        '''
        self.migrator.upgrade()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage:")
        print("  python upgrade.py <message>   - Create and apply a new migration")
        print("  python upgrade.py create <message> - Create a new migration file without applying it")
        print("  python upgrade.py upgrade     - Upgrade to head")
        sys.exit(1)

    upgrade_migrations = UpgradeMigrations()

    if sys.argv[1] == "upgrade":
        upgrade_migrations.upgrade_head()
    elif sys.argv[1] == "create":
        upgrade_migrations.create_migration(sys.argv[2])
    else:
        upgrade_migrations.upgrade(sys.argv[1])
