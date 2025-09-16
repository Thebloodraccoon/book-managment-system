from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.repository import BaseRepository
from app.models.author_model import Author
from app.models.book_model import Book


class BookRepository(BaseRepository[Book]):
    """Repository for Book entities with advanced queries."""

    def __init__(self, db: Session):
        super().__init__(Book, db)

    def get_by_title(self, title: str) -> Book | None:
        """Get books by exact title match."""
        return self.db.query(Book).filter(
            func.lower(Book.title) == func.lower(title)
        ).first()

    def get_by_author_id(self, author_id: int) -> list[Book]:
        """Get all books by author ID."""
        return self.db.query(Book).filter(Book.author_id == author_id).all()

    def get_by_genre(self, genre: str) -> list[Book]:
        """Get all books by genre."""
        return self.db.query(Book).filter(Book.genre == genre).all()

    def get_by_year_range(self, year_min: int, year_max: int) -> list[Book]:
        """Get books published within a year range."""
        return self.db.query(Book).filter(
            Book.published_year >= year_min,
            Book.published_year <= year_max
        ).all()

    def search_by_title(self, title: str) -> list[Book]:
        """Search books by partial title match."""
        return self.db.query(Book).filter(
            func.lower(Book.title).contains(func.lower(title))
        ).all()

    def get_all_with_authors(self, skip: int = 0, limit: int = 100) -> list[Book]:
        """Get all books with their author information eagerly loaded."""
        return (
            self.db.query(Book)
            .options(joinedload(Book.author))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id_with_author(self, book_id: int) -> Book | None:
        """Get books by ID with author information eagerly loaded."""
        return (
            self.db.query(Book)
            .options(joinedload(Book.author))
            .filter(Book.id == book_id)
            .first()
        )

    def count_by_author(self, author_id: int) -> int:
        """Count books by author."""
        return self.db.query(Book).filter(Book.author_id == author_id).count()

    def get_latest_books(self, limit: int = 10) -> list[Book]:
        """Get most recently added books."""
        return (
            self.db.query(Book)
            .options(joinedload(Book.author))
            .order_by(Book.created_at.desc())
            .limit(limit)
            .all()
        )


class AuthorRepository(BaseRepository[Author]):
    """Repository for Author entities."""

    def __init__(self, db: Session):
        super().__init__(Author, db)

    def get_by_name(self, name: str) -> Author | None:
        """Get author by exact name match."""
        return self.db.query(Author).filter(
            func.lower(Author.name) == func.lower(name)
        ).first()

    def search_by_name(self, name: str) -> list[Author]:
        """Search authors by partial name match."""
        return self.db.query(Author).filter(
            func.lower(Author.name).contains(func.lower(name))
        ).all()

    def get_authors_with_books(self) -> list[Author]:
        """Get all authors who have written books."""
        return (
            self.db.query(Author)
            .join(Book)
            .distinct()
            .all()
        )

    def get_authors_with_book_count(self) -> list[tuple[Author, int]]:
        """Get all authors with their books counts."""
        return (
            self.db.query(Author, func.count(Book.id).label('book_count'))
            .outerjoin(Book)
            .group_by(Author.id)
            .all()
        )

    def delete_if_no_books(self, author_id: int) -> bool:
        """Delete author if they have no books associated."""
        book_count = self.db.query(Book).filter(Book.author_id == author_id).count()

        if book_count == 0:
            author = self.get_by_id(author_id)
            if author:
                return self.delete(author)
        return False