"""
BrowseTerm Database Package
Main entry point for the browseterm-db package
"""
# Note: These imports will work when the package is installed
# They use relative imports within the package
from browseterm_db.operations.all_operations import (
    UserOps,
    ContainerOps, 
    OrdersOps,
    SubscriptionOps,
    SubscriptionTypeOps,
    DBOperations,
    OperationResult,
    DBConfig
)

from browseterm_db.models.all_models import (
    User,
    SubscriptionType,
    Subscription,
    Container,
    Orders,
    Base
)

__version__ = "0.1.0"
__all__ = [
    # Operations
    'UserOps',
    'ContainerOps', 
    'OrdersOps',
    'SubscriptionOps',
    'SubscriptionTypeOps',
    'DBOperations',
    'OperationResult',
    'DBConfig',
    # Models
    'User',
    'SubscriptionType',
    'Subscription',
    'Container',
    'Orders',
    'Base'
]
