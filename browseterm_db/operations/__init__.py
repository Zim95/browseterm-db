"""
Database operations module
Contains base operations class and imports all models for table creation
"""
# builtins
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# logging
import logging

# sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.models.all_models import *


logger = logging.getLogger(__name__)


class OperationResult:
    """
    Result object for database operations
    """
    def __init__(self, success: bool, message: str = "", data: Any = None, error: str = ""):
        self.success = success
        self.message = message
        self.data = data
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error
        }


class DBOperations(ABC):
    """
    Abstract base class for database operations.
    All model operations classes should inherit from this class and implement the abstract methods.
    This class provides session management with proper commits and rollbacks.
    """

    def __init__(self, db_config: DBConfig) -> None:
        """
        Initialize the DBOperations class.
        """
        self.db_config: DBConfig = db_config
        self.session: Optional[Session] = None

    def _get_session(self) -> Session:
        """Get a database session"""
        # Import all models to ensure they are registered with SQLAlchemy
        if not self.session:
            self.session = self.db_config.get_db_session()
        return self.session
    
    def _close_session(self):
        """Close the database session"""
        if self.session:
            self.session.close()
            self.session = None
    
    def _commit_and_close(self) -> OperationResult:
        """Commit transaction and close session"""
        try:
            if self.session:
                self.session.commit()
                self._close_session()
            return OperationResult(success=True, message="Operation completed successfully")
        except SQLAlchemyError as e:
            logger.error(f"Commit failed: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Commit failed: {str(e)}")
    
    def _rollback_and_close(self) -> OperationResult:
        """Rollback transaction and close session"""
        try:
            if self.session:
                self.session.rollback()
                self._close_session()
            return OperationResult(success=False, message="Transaction rolled back")
        except SQLAlchemyError as e:
            logger.error(f"Rollback failed: {str(e)}")
            if self.session:
                self.session.close()
                self.session = None
            return OperationResult(success=False, error=f"Rollback failed: {str(e)}")
    
    @abstractmethod
    def find(self, filters: Dict[str, Any], limit: Optional[int] = None, 
             offset: Optional[int] = None) -> OperationResult:
        """
        Find multiple records based on filters
        
        Args:
            filters: Dictionary of field-value pairs to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            OperationResult with list of records or error
        """
        pass
    
    @abstractmethod
    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """
        Find a single record based on filters
        
        Args:
            filters: Dictionary of field-value pairs to filter by
            
        Returns:
            OperationResult with single record or error
        """
        pass
    
    @abstractmethod
    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """
        Insert a single record
        
        Args:
            data: Dictionary containing the data to insert
            
        Returns:
            OperationResult with created record or error
        """
        pass
    
    @abstractmethod
    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """
        Insert multiple records
        
        Args:
            data_list: List of dictionaries containing the data to insert
            
        Returns:
            OperationResult with created records or error
        """
        pass
    
    @abstractmethod
    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """
        Update records based on filters
        
        Args:
            filters: Dictionary of field-value pairs to identify records
            data: Dictionary containing the updated data
            
        Returns:
            OperationResult with updated records or error
        """
        pass
    
    @abstractmethod
    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """
        Update multiple records with different data
        
        Args:
            updates: List of dictionaries, each containing 'filters' and 'data' keys
                    Format: [{'filters': {...}, 'data': {...}}, ...]
            
        Returns:
            OperationResult with updated records or error
        """
        pass
    
    @abstractmethod
    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """
        Delete records based on filters
        
        Args:
            filters: Dictionary of field-value pairs to identify records
            
        Returns:
            OperationResult with success/failure status
        """
        pass
    
    @abstractmethod
    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """
        Delete multiple records with different filters
        
        Args:
            filter_list: List of filter dictionaries
            
        Returns:
            OperationResult with success/failure status
        """
        pass
