from typing import Any, Generic, Protocol, TypeVar

from sqlalchemy import Column
from sqlalchemy.orm import Session


class ModelProtocol(Protocol):
    """Protocol for determining the basic attributes of the model."""

    id: Column[int]


ModelType = TypeVar("ModelType", bound=ModelProtocol)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common CRUD operations for SQLAlchemy models."""

    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, model_id: int) -> ModelType | None:
        """Retrieve a single record by its primary key ID."""
        return self.db.query(self.model).filter(self.model.id == model_id).first()

    def get_all(self, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Retrieve multiple records with pagination support."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count_all(self) -> int:
        """Count the total number of records in the table."""
        return self.db.query(self.model).count()

    def create(self, obj_data: dict[str, Any]) -> ModelType:
        """Create a new record in the database."""

        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ModelType, update_data: dict[str, Any]) -> ModelType:
        """Update an existing record with new values."""

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, db_obj: ModelType) -> bool:
        """Delete a record from the database."""

        self.db.delete(db_obj)
        self.db.commit()
        return True

    def exists_by_id(self, model_id: int) -> bool:
        """Check if a record exists by its primary key ID."""
        return self.db.query(self.model).filter(self.model.id == model_id).first() is not None

    def filter_by_fields(self, **filters) -> list[ModelType]:
        """Filter records by multiple field values using exact matching."""

        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        return query.all()
