"""
Utility module for managing subscription types and images from JSON configuration files.
This module maintains the state of subscription_types and images tables based on JSON files.
"""

# builtins
import json
import os
import sys
from typing import Dict, List, Any
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# dotenv
from dotenv import load_dotenv

# local
from browseterm_db.operations.subscription_type_ops import SubscriptionTypeOps
from browseterm_db.operations.image_ops import ImageOps
from browseterm_db.common.config import DBConfig
from browseterm_db.models.subscription_types import SubscriptionTypeCurrency
from browseterm_db.operations import DBOperations, OperationResult


load_dotenv('.env')
logger = logging.getLogger(__name__)


class DBStateManager:
    """
    Database state manager for maintaining subscription types and images from JSON files
    """

    def __init__(self, db_config: DBConfig):
        self.db_config: DBConfig = db_config
        self.subscription_type_ops: DBOperations = SubscriptionTypeOps(db_config)
        self.image_ops: DBOperations = ImageOps(db_config)

    def load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load data from JSON file"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"JSON file {file_path} does not exist")
                return []
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                logger.error(f"JSON file {file_path} should contain a list")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []

    def get_state_list(self, table_name: str) -> list[dict]:
        try:
            base_file_dir: str = os.path.dirname(os.path.abspath(__file__))
            table_name_file_mapping: dict = {
                "images": f"{base_file_dir}/states/images.json",
                "subscription_types": f"{base_file_dir}/states/subscription_types.json"
            }
            file_path: str = table_name_file_mapping.get(table_name)
            if not file_path:
                raise KeyError(f"Invalid table_name: {table_name}")
            state_list: list = self.load_json_file(file_path)
            if not state_list:
                raise ValueError(f"No data found in {file_path}")
            return state_list
        except KeyError as ke:
            raise KeyError(f"KeyError getting state_list: {ke}")
        except ValueError as ve:
            raise ValueError(f"ValueError getting state_list: {ve}")
        except Exception as e:
            raise Exception(f"Error getting state_list: {e}")

    def get_db_list(self, table_name: str) -> list[dict]:
        try:
            table_name_db_ops_mapping: dict = {
                "images": self.image_ops,
                "subscription_types": self.subscription_type_ops
            }
            db_ops: DBOperations | None = table_name_db_ops_mapping.get(table_name)
            if not db_ops:
                raise KeyError(f"Invalid table_name: {table_name}")
            db_items: OperationResult = db_ops.find({})
            if db_items.error:
                raise Exception(f"Error getting data for: {table_name}")
            return db_items.data
        except KeyError as ke:
            raise KeyError(f"KeyError getting state_list: {ke}")
        except ValueError as ve:
            raise ValueError(f"ValueError getting state_list: {ve}")
        except Exception as e:
            raise Exception(f"Error getting state_list: {e}")

    def find_differences(self, state_list: list[dict], db_list: list[dict], table_name: str) -> dict:
        """
        1. Find items that are unique to the state list.
        2. Find items that are unique to the db list.
        3. Find items that are common in both.
        """
        try:
            # Handle empty lists
            if not state_list and not db_list:
                return {
                    "unique_to_state_list": set(),
                    "unique_to_db_list": set(),
                    "common_to_state_db_list": set()
                }
            state_list_names: set[str] = {item["name"] for item in state_list} if state_list else set()
            db_list_names: set[str] = {item["name"] for item in db_list} if db_list else set()
            unique_to_state_list: set[str] = state_list_names - db_list_names
            unique_to_db_list: set[str] = db_list_names - state_list_names
            common_to_state_db_list: set[str] = state_list_names & db_list_names
            return {
                "unique_to_state_list": unique_to_state_list,
                "unique_to_db_list": unique_to_db_list,
                "common_to_state_db_list": common_to_state_db_list
            }
        except Exception as e:
            raise Exception(f"Error finding differences for {table_name}: {e}")

    def create_items(self, state_list: list[dict], table_name: str, differences: dict) -> None:
        try:
            table_name_ops_mapping: dict = {
                "images": self.image_ops,
                "subscription_types": self.subscription_type_ops
            }
            ops: DBOperations | None = table_name_ops_mapping.get(table_name)
            if not ops:
                raise KeyError(f"Invalid table_name: {table_name}")
            state_list_dict: dict[str, dict] = {item["name"]: item for item in state_list}
            names: set[str] = differences["unique_to_state_list"]
            for name in names:
                item: dict = state_list_dict.get(name)
                if item:
                    result: OperationResult = ops.insert(item)
                    if result.error:
                        raise Exception(f"Error creating item: {result.error}")
        except KeyError as ke:
            raise KeyError(f"KeyError creating items for {table_name}: {ke}")
        except ValueError as ve:
            raise ValueError(f"ValueError creating items for {table_name}: {ve}")
        except Exception as e:
            raise Exception(f"Error creating items for {table_name}: {e}")

    def update_items(self, state_list: list[dict], db_list: list[dict], table_name: str, differences: dict) -> None:
        try:
            table_name_ops_mapping: dict = {
                "images": self.image_ops,
                "subscription_types": self.subscription_type_ops
            }
            ops: DBOperations | None = table_name_ops_mapping.get(table_name)
            if not ops:
                raise KeyError(f"Invalid table_name: {table_name}")
            state_list_dict: dict[str, dict] = {item["name"]: item for item in state_list}
            db_list_dict: dict[str, dict] = {item["name"]: item for item in db_list}
            names: set[str] = differences["common_to_state_db_list"]
            for name in names:
                item: dict = state_list_dict.get(name)
                if not item:
                    item = db_list_dict.get(name)
                if not item:
                    raise ValueError(f"Item not found in state_list or db_list: {name}")
                result: OperationResult = ops.update({"name": name}, item)
                if result.error:
                    raise Exception(f"Error updating item: {result.error}")
        except KeyError as ke:
            raise KeyError(f"KeyError creating items for {table_name}: {ke}")
        except ValueError as ve:
            raise ValueError(f"ValueError creating items for {table_name}: {ve}")
        except Exception as e:
            raise Exception(f"Error creating items for {table_name}: {e}")

    def delete_items(self, db_list: list[dict], table_name: str, differences: dict) -> None:
        try:
            table_name_ops_mapping: dict = {
                "images": self.image_ops,
                "subscription_types": self.subscription_type_ops
            }
            ops: DBOperations | None = table_name_ops_mapping.get(table_name)
            if not ops:
                raise KeyError(f"Invalid table_name: {table_name}")
            db_list_dict: dict[str, dict] = {item["name"]: item for item in db_list}
            names: set[str] = differences["unique_to_db_list"]
            for name in names:
                item: dict = db_list_dict.get(name)
                if item:
                    result: OperationResult = ops.soft_delete({"name": name})
                    if result.error:
                        raise Exception(f"Error deleting item: {result.error}")
        except KeyError as ke:
            raise KeyError(f"KeyError deleting items for {table_name}: {ke}")
        except ValueError as ve:
            raise ValueError(f"ValueError deleting items for {table_name}: {ve}")
        except Exception as e:
            raise Exception(f"Error deleting items for {table_name}: {e}")


def update_subscription_types(db_state_manager: DBStateManager) -> None:
    try:
        state_list: list[dict] = db_state_manager.get_state_list('subscription_types')
        db_list: list[dict] = db_state_manager.get_db_list('subscription_types')
        differences: dict = db_state_manager.find_differences(state_list, db_list, 'subscription_types')
        db_state_manager.create_items(state_list, 'subscription_types', differences)
        db_state_manager.update_items(state_list, db_list, 'subscription_types', differences)
        db_state_manager.delete_items(db_list, 'subscription_types', differences)
    except Exception as e:
        raise Exception(f"Error updating subscription types: {e}")

def update_images(db_state_manager: DBStateManager) -> None:
    try:
        state_list: list[dict] = db_state_manager.get_state_list('images')
        db_list: list[dict] = db_state_manager.get_db_list('images')
        differences: dict = db_state_manager.find_differences(state_list, db_list, 'images')
        db_state_manager.create_items(state_list, 'images', differences)
        db_state_manager.update_items(state_list, db_list, 'images', differences)
        db_state_manager.delete_items(db_list, 'images', differences)
    except Exception as e:
        raise Exception(f"Error updating images: {e}")

if __name__ == "__main__":
    db_config: DBConfig = DBConfig(
        username=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_DATABASE')
    )
    db_state_manager: DBStateManager = DBStateManager(db_config)
    print("Updating subscription types...")
    update_subscription_types(db_state_manager)
    print("Updating images...")
    update_images(db_state_manager)
    print("Done")
