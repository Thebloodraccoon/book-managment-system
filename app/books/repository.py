from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.models.author_model import Author
from app.models.book_model import Book


class BookRepository(BaseRepository[Book]):
    """Repository for Book entities with advanced queries."""

    def __init__(self, db: Session):
        super().__init__(Book, db)

    def get_by_id_with_author(self, book_id: int) -> Book | None:
        """Get book by ID with author information eagerly loaded."""
        from sqlalchemy.orm import joinedload

        return self.db.query(Book).options(joinedload(Book.author)).filter(Book.id == book_id).first()

    def get_books(
        self,
        page: int = 0,
        size: int = 10,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        sort_by: str = "title",
        sort_order: str = "asc",
    ):
        """Get books with filtering, pagination, and sorting using raw SQL."""

        query = """
                SELECT b.*, a.name as author_name, a.created_at as author_created_at, a.updated_at as author_updated_at
                FROM books b
                         JOIN authors a ON b.author_id = a.id
                WHERE 1 = 1
                """
        params = {}

        if title:
            query += " AND LOWER(b.title) LIKE LOWER(:title)"
            params["title"] = f"%{title}%"

        if author:
            query += " AND LOWER(a.name) LIKE LOWER(:author)"
            params["author"] = f"%{author}%"

        if genre:
            query += " AND b.genre = :genre"
            params["genre"] = genre

        if year_min:
            query += " AND b.published_year >= :year_min"
            params["year_min"] = year_min  # type: ignore

        if year_max:
            query += " AND b.published_year <= :year_max"
            params["year_max"] = year_max  # type: ignore

        sort_column = "b.title"
        if sort_by == "published_year":
            sort_column = "b.published_year"
        elif sort_by == "author":
            sort_column = "a.name"

        query += f" ORDER BY {sort_column} {sort_order.upper()}"
        query += " LIMIT :limit OFFSET :offset"

        params["limit"] = size  # type: ignore
        params["offset"] = page * size  # type: ignore

        result = self.db.execute(text(query), params)
        return result.fetchall()


class AuthorRepository(BaseRepository[Author]):
    """Repository for Author entities."""

    def __init__(self, db: Session):
        super().__init__(Author, db)

    def get_by_name(self, name: str) -> Author | None:
        """Get author by exact name match."""
        return self.db.query(Author).filter(func.lower(Author.name) == func.lower(name)).first()
