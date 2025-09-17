import csv
from io import StringIO
import json

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.books.repository import AuthorRepository, BookRepository
from app.books.schemas import BookCreate, BookImportData, BookResponse, BookUpdate, BulkImportResponse
from app.exceptions.book_exceptions import (
    BookAlreadyExistsException,
    BookNotFoundException,
    EmptyFileException,
    InvalidFileFormatException,
)
from app.models.book_model import GenreEnum


class BookService:
    """Business logic for Book management."""

    def __init__(self, db: Session):
        self.book_repo = BookRepository(db)
        self.author_repo = AuthorRepository(db)
        self.db = db

    def create_book(self, data: BookCreate) -> BookResponse:
        """Create a new book."""
        author = self.author_repo.get_by_name(data.author_name)
        if author:
            existing_book = (
                self.db.query(self.book_repo.model)
                .filter(
                    func.lower(self.book_repo.model.title) == func.lower(data.title),
                    self.book_repo.model.author_id == author.id,
                )
                .first()
            )
            if existing_book:
                raise BookAlreadyExistsException(data.title, data.author_name)

        if not author:
            author = self.author_repo.create({"name": data.author_name})

        book_data = data.model_dump(exclude={"author_name"})
        book_data["author_id"] = author.id
        book = self.book_repo.create(book_data)

        return BookResponse.model_validate(book)

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
    ) -> list[BookResponse]:
        """Get books with filtering, pagination, and sorting using raw SQL."""

        if genre:
            try:
                genre = GenreEnum[genre.upper().replace("-", "_")]
            except KeyError:
                raise ValueError(f"Invalid genre: {genre}")

        books = self.book_repo.get_books(
            page=page,
            size=size,
            title=title,
            author=author,
            genre=genre,
            year_min=year_min,
            year_max=year_max,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return [self._build_book_response(book) for book in books]

    def get_book_by_id(self, book_id: int) -> BookResponse:
        """Get book by ID."""
        book = self.book_repo.get_by_id_with_author(book_id)
        if not book:
            raise BookNotFoundException(book_id=book_id)
        return BookResponse.model_validate(book)

    def update_book(self, book_id: int, data: BookUpdate) -> BookResponse:
        """Update book."""
        book = self.book_repo.get_by_id(book_id)
        if not book:
            raise BookNotFoundException(book_id=book_id)

        update_data = data.model_dump(exclude_unset=True)

        if "author_name" in update_data:
            author_name = update_data.pop("author_name")
            author = self.author_repo.get_by_name(author_name)
            if not author:
                author = self.author_repo.create({"name": author_name})
            update_data["author_id"] = author.id

        updated_book = self.book_repo.update(book, update_data)
        return BookResponse.model_validate(updated_book)

    def delete_book(self, book_id: int) -> bool:
        """Delete book."""
        book = self.book_repo.get_by_id(book_id)
        if not book:
            raise BookNotFoundException(book_id=book_id)
        return self.book_repo.delete(book)

    async def bulk_import_books(self, file: UploadFile) -> BulkImportResponse:
        """Bulk import books from CSV or JSON file."""
        if not file.filename:
            raise EmptyFileException()

        if not (file.filename.endswith(".csv") or file.filename.endswith(".json")):
            raise InvalidFileFormatException(file.filename)

        content = await file.read()
        content_str = content.decode("utf-8")

        books_data = self._parse_csv(content_str) if file.filename.endswith(".csv") else self._parse_json(content_str)

        successful_imports = 0
        errors = []

        for i, book_data in enumerate(books_data):
            try:
                validated_data = BookImportData.model_validate(book_data)
                book_create = BookCreate(
                    title=validated_data.title,
                    author_name=validated_data.author_name,
                    published_year=validated_data.published_year,
                    genre=GenreEnum[validated_data.genre.upper().replace("-", "_")],
                )
                self.create_book(book_create)
                successful_imports += 1
            except Exception as e:
                errors.append(f"Row {i + 1}: {str(e)}")

        return BulkImportResponse(
            total_processed=len(books_data),
            successful_imports=successful_imports,
            failed_imports=len(books_data) - successful_imports,
            errors=errors,
        )

    @classmethod
    def _parse_csv(cls, content: str) -> list[dict]:
        """Parse CSV content."""
        csv_reader = csv.DictReader(StringIO(content))
        return [
            {
                "title": row.get("title", "").strip(),
                "author_name": row.get("author_name", "").strip(),
                "published_year": int(row.get("published_year", 0)),
                "genre": row.get("genre", "").strip(),
            }
            for row in csv_reader
        ]

    @classmethod
    def _parse_json(cls, content: str) -> list[dict]:
        """Parse JSON content."""
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("JSON must contain an array of book objects")
        return data

    @classmethod
    def _build_book_response(cls, book_row) -> BookResponse:
        """Build BookResponse from raw SQL result."""
        from app.books.schemas import AuthorResponse
        from app.models.book_model import GenreEnum

        author_data = AuthorResponse(
            id=book_row.author_id,
            name=book_row.author_name,
            created_at=book_row.author_created_at,
            updated_at=book_row.author_updated_at,
        )

        genre_value = book_row.genre
        if isinstance(genre_value, str):
            try:
                genre_enum = GenreEnum[genre_value]
            except KeyError:
                genre_enum = GenreEnum(genre_value)
        else:
            genre_enum = genre_value

        return BookResponse(
            id=book_row.id,
            title=book_row.title,
            published_year=book_row.published_year,
            genre=genre_enum,
            author_id=book_row.author_id,
            author=author_data,
            created_at=book_row.created_at,
            updated_at=book_row.updated_at,
        )
