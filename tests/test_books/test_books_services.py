from io import BytesIO

from fastapi import UploadFile
import pytest

from app.books.schemas import BookCreate, BookUpdate
from app.books.services import BookService
from app.exceptions.book_exceptions import (
    BookAlreadyExistsException,
    BookNotFoundException,
    EmptyFileException,
    InvalidFileFormatException,
)
from app.models.book_model import GenreEnum


def test_create_book_success(db_session):
    service = BookService(db_session)
    data = BookCreate(title="New Book", author_name="New Author", published_year=2023, genre=GenreEnum.FICTION)

    book = service.create_book(data)

    assert book.title == "New Book"
    assert book.author.name == "New Author"
    assert book.published_year == 2023
    assert book.genre == GenreEnum.FICTION


def test_create_book_with_existing_author(db_session, test_author):
    service = BookService(db_session)
    data = BookCreate(title="Another Book", author_name=test_author.name, published_year=2023, genre=GenreEnum.FANTASY)

    book = service.create_book(data)

    assert book.author.id == test_author.id
    assert book.author.name == test_author.name


def test_create_book_duplicate_title_same_author(db_session, test_book):
    service = BookService(db_session)
    data = BookCreate(
        title=test_book.title, author_name=test_book.author.name, published_year=2023, genre=GenreEnum.FICTION
    )

    with pytest.raises(BookAlreadyExistsException):
        service.create_book(data)


def test_get_books_success(db_session, test_books_multiple):
    service = BookService(db_session)

    books = service.get_books(page=0, size=10)

    assert len(books) == 5
    assert all(hasattr(book, "author") for book in books)


@pytest.mark.parametrize(
    "filters,expected_count",
    [
        ({"title": "1984"}, 1),
        ({"author": "Tolkien"}, 1),
        ({"year_min": 1900, "year_max": 1950}, 3),
        ({"title": "nonexistent"}, 0),
    ],
)
def test_get_books_with_filters(db_session, test_books_multiple, filters, expected_count):
    service = BookService(db_session)

    books = service.get_books(**filters)

    assert len(books) == expected_count


@pytest.mark.parametrize(
    "sort_by,sort_order,expected_first",
    [
        ("title", "asc", "1984"),
        ("title", "desc", "The Hobbit"),
        ("published_year", "asc", "Pride and Prejudice"),
        ("published_year", "desc", "Dune"),
        ("author", "asc", "Frank Herbert"),
        ("author", "desc", "Sun Tzu"),
    ],
)
def test_get_books_sorting(db_session, test_books_multiple, sort_by, sort_order, expected_first):
    service = BookService(db_session)

    books = service.get_books(sort_by=sort_by, sort_order=sort_order)

    if sort_by == "author":
        assert books[0].author.name.startswith(expected_first.split()[0])
    else:
        if sort_by == "title":
            assert books[0].title == expected_first
        elif sort_by == "published_year":
            expected_book = next(b for b in test_books_multiple if b.title == expected_first)
            assert books[0].published_year == expected_book.published_year


def test_get_books_pagination(db_session, test_books_multiple):
    service = BookService(db_session)

    # First page
    page1 = service.get_books(page=0, size=2)
    assert len(page1) == 2

    # Second page
    page2 = service.get_books(page=1, size=2)
    assert len(page2) == 2

    # No overlap between pages
    page1_titles = {book.title for book in page1}
    page2_titles = {book.title for book in page2}
    assert page1_titles.isdisjoint(page2_titles)


def test_get_book_by_id_success(db_session, test_book):
    service = BookService(db_session)

    book = service.get_book_by_id(test_book.id)

    assert book.id == test_book.id
    assert book.title == test_book.title
    assert book.author.name == test_book.author.name


def test_get_book_by_id_not_found(db_session):
    service = BookService(db_session)

    with pytest.raises(BookNotFoundException):
        service.get_book_by_id(99999)


@pytest.mark.parametrize(
    "update_data,expected",
    [
        (BookUpdate(title="Updated Title"), {"title": "Updated Title"}),
        (BookUpdate(published_year=2024), {"published_year": 2024}),
        (BookUpdate(genre=GenreEnum.SCIENCE), {"genre": GenreEnum.SCIENCE}),
        (BookUpdate(author_name="New Author"), {"author_name": "New Author"}),
        (
            BookUpdate(title="Full Update", published_year=2024, genre=GenreEnum.HISTORY),
            {"title": "Full Update", "published_year": 2024, "genre": GenreEnum.HISTORY},
        ),
    ],
)
def test_update_book_success(db_session, test_book, update_data, expected):
    service = BookService(db_session)

    updated_book = service.update_book(test_book.id, update_data)

    for field, value in expected.items():
        if field == "author_name":
            assert updated_book.author.name == value
        else:
            assert getattr(updated_book, field) == value


def test_update_book_with_new_author(db_session, test_book):
    service = BookService(db_session)
    update_data = BookUpdate(author_name="Completely New Author")

    updated_book = service.update_book(test_book.id, update_data)

    assert updated_book.author.name == "Completely New Author"


def test_update_book_not_found(db_session):
    service = BookService(db_session)
    update_data = BookUpdate(title="Ghost Title")

    with pytest.raises(BookNotFoundException):
        service.update_book(99999, update_data)


def test_delete_book_success(db_session, test_book):
    service = BookService(db_session)

    result = service.delete_book(test_book.id)

    assert result is True
    with pytest.raises(BookNotFoundException):
        service.get_book_by_id(test_book.id)


def test_delete_book_not_found(db_session):
    service = BookService(db_session)

    with pytest.raises(BookNotFoundException):
        service.delete_book(99999)


@pytest.mark.asyncio
async def test_bulk_import_json_success(db_session):
    service = BookService(db_session)

    json_data = """[
        {
            "title": "Book 1",
            "author_name": "Author 1",
            "published_year": 2020,
            "genre": "Fiction"
        },
        {
            "title": "Book 2",
            "author_name": "Author 2",
            "published_year": 2021,
            "genre": "Science"
        }
    ]"""

    file_content = BytesIO(json_data.encode("utf-8"))
    upload_file = UploadFile(filename="books.json", file=file_content, headers={"content-type": "application/json"})

    result = await service.bulk_import_books(upload_file)

    assert result.total_processed == 2
    assert result.successful_imports == 2
    assert result.failed_imports == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_bulk_import_csv_success(db_session):
    service = BookService(db_session)

    csv_data = """title,author_name,published_year,genre
Book CSV 1,CSV Author 1,2020,Fiction
Book CSV 2,CSV Author 2,2021,Science"""

    file_content = BytesIO(csv_data.encode("utf-8"))
    upload_file = UploadFile(filename="books.csv", file=file_content, headers={"content-type": "text/csv"})

    result = await service.bulk_import_books(upload_file)

    assert result.total_processed == 2
    assert result.successful_imports == 2
    assert result.failed_imports == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_bulk_import_with_errors(db_session):
    service = BookService(db_session)

    json_data = """[
        {
            "title": "Valid Book",
            "author_name": "Valid Author",
            "published_year": 2020,
            "genre": "Fiction"
        },
        {
            "title": "",
            "author_name": "Invalid Author",
            "published_year": 2021,
            "genre": "Science"
        },
        {
            "title": "Another Invalid",
            "author_name": "Another Author",
            "published_year": 1700,
            "genre": "Fiction"
        }
    ]"""

    file_content = BytesIO(json_data.encode("utf-8"))
    upload_file = UploadFile(
        filename="books_with_errors.json", file=file_content, headers={"content-type": "application/json"}
    )

    result = await service.bulk_import_books(upload_file)

    assert result.total_processed == 3
    assert result.successful_imports == 1
    assert result.failed_imports == 2
    assert len(result.errors) == 2


@pytest.mark.asyncio
async def test_bulk_import_empty_filename(db_session):
    service = BookService(db_session)

    file_content = BytesIO(b"test content")
    upload_file = UploadFile(filename=None, file=file_content)

    with pytest.raises(EmptyFileException):
        await service.bulk_import_books(upload_file)


@pytest.mark.asyncio
async def test_bulk_import_invalid_format(db_session):
    service = BookService(db_session)

    file_content = BytesIO(b"test content")
    upload_file = UploadFile(filename="books.txt", file=file_content)

    with pytest.raises(InvalidFileFormatException):
        await service.bulk_import_books(upload_file)


def test_parse_csv():
    csv_content = """title,author_name,published_year,genre
Book 1,Author 1,2020,Fiction
Book 2,Author 2,2021,Science"""

    result = BookService._parse_csv(csv_content)

    assert len(result) == 2
    assert result[0]["title"] == "Book 1"
    assert result[0]["author_name"] == "Author 1"
    assert result[0]["published_year"] == 2020
    assert result[0]["genre"] == "Fiction"


def test_parse_json():
    json_content = """[
        {
            "title": "Book 1",
            "author_name": "Author 1",
            "published_year": 2020,
            "genre": "Fiction"
        }
    ]"""

    result = BookService._parse_json(json_content)

    assert len(result) == 1
    assert result[0]["title"] == "Book 1"


def test_parse_json_invalid_format():
    json_content = """{"not": "an array"}"""

    with pytest.raises(ValueError, match="JSON must contain an array"):
        BookService._parse_json(json_content)
