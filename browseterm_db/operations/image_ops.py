"""
Image operations - Database operations for Image model
"""
# builtins
import uuid
from typing import Dict, List, Any, Optional
import logging

# sqlalchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, Query

# local
from browseterm_db.models.images import Image
from browseterm_db.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)


class ImageOps(DBOperations):
    """
    Image operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert values to appropriate types"""
        insert_conversion_map: dict = {
            'id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def find(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        to_dict: bool = True
    ) -> OperationResult:
        """Find multiple images based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Image)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Image, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Image, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            images: List[Image] = query.all()
            image_list: List[Dict[str, Any]] = [image.to_dict() for image in images] if to_dict else images
            self._close_session()
            return OperationResult(
                success=True,
                message=f"Found {len(image_list)} images",
                data=image_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any], to_dict: bool = True) -> OperationResult:
        """Find a single image based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Image)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Image, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Image, key) == converted_value)
            image: Optional[Image] = query.first()
            if not image:
                self._close_session()
                return OperationResult(
                    success=False,
                    error="Image not found",
                    data=None
                )
            image_data: Dict[str, Any] = image.to_dict() if to_dict else image
            self._close_session()
            return OperationResult(
                success=True,
                message="Image found",
                data=image_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single image"""
        try:
            session: Session = self._get_session()
            # Create image instance
            image: Image = Image(
                name=data.get('name'),
                image=data.get('image'),
                is_active=data.get('is_active', True)
            )
            session.add(image)
            session.flush()
            result_data: Dict[str, Any] = image.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message="Image created successfully",
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error creating image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple images"""
        try:
            session: Session = self._get_session()
            images: List[Image] = []
            for data in data_list:
                image: Image = Image(
                    name=data.get('name'),
                    image=data.get('image'),
                    is_active=data.get('is_active', True)
                )
                images.append(image)
            session.add_all(images)
            session.flush()
            result_data: List[Dict[str, Any]] = [image.to_dict() for image in images]
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Created {len(images)} images successfully",
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error creating images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update(self, filters: Dict[str, Any], updates: Dict[str, Any]) -> OperationResult:
        """Update a single image based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Image)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Image, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Image, key) == converted_value)
            image: Optional[Image] = query.first()
            if not image:
                self._close_session()
                return OperationResult(success=False, error="Image not found")
            # Apply updates
            for key, value in updates.items():
                if hasattr(image, key) and key not in ['id', 'created_at']:
                    converted_value = self._convert_update_value(key, value)
                    setattr(image, key, converted_value)
            session.flush()
            result_data: Dict[str, Any] = image.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message="Image updated successfully",
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error updating image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error updating image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, filters: Dict[str, Any], updates: Dict[str, Any]) -> OperationResult:
        """Update multiple images based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Image)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Image, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Image, key) == converted_value)
            # Build update dictionary with converted values
            update_dict: Dict[str, Any] = {}
            for key, value in updates.items():
                if hasattr(Image, key) and key not in ['id', 'created_at']:
                    converted_value = self._convert_update_value(key, value)
                    update_dict[key] = converted_value
            # Execute update
            updated_count: int = query.update(update_dict, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Updated {updated_count} images successfully",
                data={"updated_count": updated_count}
            )
        except ValueError as e:
            logger.error(f"Value Error updating images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error updating images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Hard delete a single image based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Image)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Image, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Image, key) == converted_value)
            image: Optional[Image] = query.first()
            if not image:
                self._close_session()
                return OperationResult(success=False, error="Image not found")
            session.delete(image)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message="Image deleted successfully",
                data=None
            )
        except ValueError as e:
            logger.error(f"Value Error deleting image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting image: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filters: Dict[str, Any]) -> OperationResult:
        """Hard delete multiple images based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Image)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Image, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Image, key) == converted_value)
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Deleted {deleted_count} images successfully",
                data={"deleted_count": deleted_count}
            )
        except ValueError as e:
            logger.error(f"Value Error deleting images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting images: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def soft_delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Soft delete a single image by setting is_active to False"""
        return self.update(filters, {"is_active": False})

    def soft_delete_many(self, filters: Dict[str, Any]) -> OperationResult:
        """Soft delete multiple images by setting is_active to False"""
        return self.update_many(filters, {"is_active": False})
