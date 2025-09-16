from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String
)
from sqlalchemy.dialects.postgresql import ENUM

from app.settings import settings


class GenreEnum(str, Enum):
    FICTION = "Fiction"
    NON_FICTION = "Non-Fiction"
    SCIENCE = "Science"
    HISTORY = "History"
    BIOGRAPHY = "Biography"
    FANTASY = "Fantasy"
    MYSTERY = "Mystery"
    ROMANCE = "Romance"
    THRILLER = "Thriller"
    CHILDREN = "Children"
    POETRY = "Poetry"
    PHILOSOPHY = "Philosophy"
    SELF_HELP = "Self-Help"
    TRAVEL = "Travel"
    COOKING = "Cooking"
    ART = "Art"
    RELIGION = "Religion"
    BUSINESS = "Business"
    HEALTH = "Health"
    TECHNOLOGY = "Technology"


class Book(settings.Base):  # type: ignore
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(500), nullable=False, index=True)
    published_year = Column(Integer, nullable=False, index=True)
    genre = Column(ENUM(GenreEnum, name="genre_enum"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey('authors.id'), nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}', author='{self.author_id}', year={self.published_year})>"
