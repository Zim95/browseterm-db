'''
Here we setup initial migrations for the project.
'''

# builtins
from dotenv import load_dotenv
import os

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import MIGRATIONS_DIR
from db_state_manager.state_manager import (
    DBStateManager,
    update_subscription_types,
    update_images
)

# load the environment variables
load_dotenv('.env')


class SetupInitialMigrations():
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
        self.migrator.reset_database()  # reset the database
        # delete all files in the versions directory
        self.migrator.reset_migrations()
        self.db_state_manager: DBStateManager = DBStateManager(self.db_config)

    def setup(self) -> None:
        '''
        Setup the initial migrations.
        '''
        # create all tables
        self.migrator.revision('Initial migration')
        # upgrade the database
        self.migrator.upgrade()

        # seed data from JSON files
        print("Creating subscription types from JSON...")
        update_subscription_types(self.db_state_manager)
        print("Creating images from JSON...")
        update_images(self.db_state_manager)
        print("Database seeding complete.")


if __name__ == "__main__":
    setup_initial_migrations = SetupInitialMigrations()
    setup_initial_migrations.setup()
