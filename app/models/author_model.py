from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String
)
from sqlalchemy.orm import relationship

from app.settings import settings


class Author(settings.Base):  # type: ignore
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    books = relationship("Book", back_populates="author")

    def __repr__(self):
        return f"<Author(id={self.id}, name='{self.name}')>"