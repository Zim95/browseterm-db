'''
Here we setup initial migrations for the project.
'''

# builtins
from dotenv import load_dotenv
import os
from typing import List, Dict, Any

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import MIGRATIONS_DIR
from browseterm_db.operations.subscription_type_ops import SubscriptionTypeOps
from browseterm_db.models.subscription_types import SubscriptionTypeCurrency
from browseterm_db.models.containers import DEFAULT_CPU_LIMIT, DEFAULT_MEMORY_LIMIT

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
        self.subscription_type_ops: SubscriptionTypeOps = SubscriptionTypeOps(self.db_config)

    def setup(self) -> None:
        '''
        Setup the initial migrations.
        '''
        # create all tables
        self.migrator.revision('Initial migration')
        # upgrade the database
        self.migrator.upgrade()

        # create default subscription types
        self.default_subscription_types: List[Dict[str, Any]] = [
            {
                "name": "Free Plan",
                "type": "free",
                "amount": 0,
                "currency": SubscriptionTypeCurrency.INR,
                "duration_days": 365,  # 1 year
                "max_containers": 1,
                "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
                "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
                "description": "Free plan with basic container limits",
                "is_active": True
            },
            {
                "name": "Basic Plan",
                "type": "basic",
                "amount": 100,
                "currency": SubscriptionTypeCurrency.INR,
                "duration_days": 30,  # 1 month
                "max_containers": 5,
                "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
                "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
                "description": "Basic plan with increased container limits",
                "is_active": True
            }
        ]
        self.subscription_type_ops.insert_many(self.default_subscription_types)


if __name__ == "__main__":
    setup_initial_migrations = SetupInitialMigrations()
    setup_initial_migrations.setup()
