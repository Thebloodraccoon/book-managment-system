from io import BytesIO

from fastapi import status
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_get_books(async_client: AsyncClient, test_books_multiple):
    response = await async_client.get("/books/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    # Check structure of response
    first_book = data[0]
    assert "id" in first_book
    assert "title" in first_book
    assert "published_year" in first_book
    assert "genre" in first_book
    assert "author" in first_book
    assert "author_id" in first_book
    assert "created_at" in first_book
    assert "updated_at" in first_book


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query_params,expected_filter",
    [
        ({"title": "1984"}, "1984"),
        ({"author": "Tolkien"}, "Tolkien"),
        ({"year_min": 1900, "year_max": 1950}, None),  # Multiple books expected
        ({"page": 0, "size": 2}, None),  # Pagination test
    ],
)
async def test_get_books_with_filters(async_client: AsyncClient, test_books_multiple, query_params, expected_filter):
    response = await async_client.get("/books/", params=query_params)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    if expected_filter:
        if query_params.get("title"):
            assert any(expected_filter in book["title"] for book in data)
        elif query_params.get("author"):
            assert any(expected_filter in book["author"]["name"] for book in data)
        elif query_params.get("genre"):
            assert any(book["genre"] == expected_filter for book in data)

    if query_params.get("size"):
        assert len(data) <= query_params["size"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sort_params",
    [
        {"sort_by": "title", "sort_order": "asc"},
        {"sort_by": "title", "sort_order": "desc"},
        {"sort_by": "published_year", "sort_order": "asc"},
        {"sort_by": "published_year", "sort_order": "desc"},
        {"sort_by": "author", "sort_order": "asc"},
        {"sort_by": "author", "sort_order": "desc"},
    ],
)
async def test_get_books_sorting(async_client: AsyncClient, test_books_multiple, sort_params):
    response = await async_client.get("/books/", params=sort_params)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 2  # Need at least 2 items to test sorting

    # Verify sorting
    if sort_params["sort_by"] == "title":
        titles = [book["title"] for book in data]
        if sort_params["sort_order"] == "asc":
            assert titles == sorted(titles)
        else:
            assert titles == sorted(titles, reverse=True)
    elif sort_params["sort_by"] == "published_year":
        years = [book["published_year"] for book in data]
        if sort_params["sort_order"] == "asc":
            assert years == sorted(years)
        else:
            assert years == sorted(years, reverse=True)


@pytest.mark.asyncio
async def test_get_book_by_id(async_client: AsyncClient, test_book):
    response = await async_client.get(f"/books/{test_book.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_book.id
    assert data["title"] == test_book.title
    assert data["author"]["name"] == test_book.author.name


@pytest.mark.asyncio
async def test_get_book_by_id_not_found(async_client: AsyncClient):
    response = await async_client.get("/books/99999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_data",
    [
        {"title": "Test Book 1", "author_name": "Test Author 1", "published_year": 2023, "genre": "Fiction"},
        {"title": "Science Book", "author_name": "Science Author", "published_year": 2020, "genre": "Science"},
    ],
)
async def test_create_book(async_client: AsyncClient, test_user_token, book_data):
    response = await async_client.post(
        "/books/", json=book_data, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["author"]["name"] == book_data["author_name"]
    assert data["published_year"] == book_data["published_year"]
    assert data["genre"] == book_data["genre"]


@pytest.mark.asyncio
async def test_create_book_unauthorized(async_client: AsyncClient):
    book_data = {
        "title": "Unauthorized Book",
        "author_name": "Unauthorized Author",
        "published_year": 2023,
        "genre": "Fiction",
    }

    response = await async_client.post("/books/", json=book_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_data,expected_error",
    [
        (
            {"title": "", "author_name": "Author", "published_year": 2023, "genre": "Fiction"},
            "Title must be a non-empty string",
        ),
        (
            {"title": "Book", "author_name": "", "published_year": 2023, "genre": "Fiction"},
            "Author name must be a non-empty string",
        ),
        (
            {"title": "Book", "author_name": "Author", "published_year": 1700, "genre": "Fiction"},
            "Published year must be between 1800",
        ),
        (
            {"title": "Book", "author_name": "Author", "published_year": 2023, "genre": "InvalidGenre"},
            "Input should be",
        ),
    ],
)
async def test_create_book_validation_errors(async_client: AsyncClient, test_user_token, invalid_data, expected_error):
    response = await async_client.post(
        "/books/", json=invalid_data, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = str(response.json())
    assert expected_error.lower() in error_detail.lower()


@pytest.mark.asyncio
async def test_create_duplicate_book(async_client: AsyncClient, test_user_token, test_book):
    duplicate_data = {
        "title": test_book.title,
        "author_name": test_book.author.name,
        "published_year": 2023,
        "genre": "Fiction",
    }

    response = await async_client.post(
        "/books/", json=duplicate_data, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_data",
    [
        {"title": "Updated Title"},
        {"published_year": 2024},
        {"genre": "Science"},
        {"author_name": "Updated Author"},
        {"title": "Fully Updated Book", "published_year": 2024, "genre": "History", "author_name": "New Author"},
    ],
)
async def test_update_book(async_client: AsyncClient, test_book, test_user_token, update_data):
    response = await async_client.put(
        f"/books/{test_book.id}", json=update_data, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    for key, value in update_data.items():
        if key == "author_name":
            assert data["author"]["name"] == value
        else:
            assert data[key] == value


@pytest.mark.asyncio
async def test_update_book_not_found(async_client: AsyncClient, test_user_token):
    update_data = {"title": "Ghost Title"}

    response = await async_client.put(
        "/books/99999", json=update_data, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_book_unauthorized(async_client: AsyncClient, test_book):
    update_data = {"title": "Unauthorized Update"}

    response = await async_client.put(f"/books/{test_book.id}", json=update_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_book(async_client: AsyncClient, test_book, test_user_token):
    response = await async_client.delete(
        f"/books/{test_book.id}", headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.text == ""

    get_response = await async_client.get(f"/books/{test_book.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_book_not_found(async_client: AsyncClient, test_user_token):
    response = await async_client.delete(
        "/books/99999", headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_book_unauthorized(async_client: AsyncClient, test_book):
    response = await async_client.delete(f"/books/{test_book.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_bulk_import_json_success(async_client: AsyncClient, test_user_token):
    json_data = """[
        {
            "title": "Bulk Book 1",
            "author_name": "Bulk Author 1",
            "published_year": 2020,
            "genre": "Fiction"
        },
        {
            "title": "Bulk Book 2",
            "author_name": "Bulk Author 2",
            "published_year": 2021,
            "genre": "Science"
        }
    ]"""

    files = {"file": ("books.json", BytesIO(json_data.encode("utf-8")), "application/json")}

    response = await async_client.post(
        "/books/bulk-import", files=files, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_processed"] == 2
    assert data["successful_imports"] == 2
    assert data["failed_imports"] == 0
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_bulk_import_csv_success(async_client: AsyncClient, test_user_token):
    csv_data = """title,author_name,published_year,genre
CSV Book 1,CSV Author 1,2020,Fiction
CSV Book 2,CSV Author 2,2021,Science"""

    files = {"file": ("books.csv", BytesIO(csv_data.encode("utf-8")), "text/csv")}

    response = await async_client.post(
        "/books/bulk-import", files=files, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_processed"] == 2
    assert data["successful_imports"] == 2
    assert data["failed_imports"] == 0
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_bulk_import_with_validation_errors(async_client: AsyncClient, test_user_token):
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

    files = {"file": ("books_errors.json", BytesIO(json_data.encode("utf-8")), "application/json")}

    response = await async_client.post(
        "/books/bulk-import", files=files, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_processed"] == 3
    assert data["successful_imports"] == 1
    assert data["failed_imports"] == 2
    assert len(data["errors"]) == 2


@pytest.mark.asyncio
async def test_bulk_import_invalid_file_format(async_client: AsyncClient, test_user_token):
    files = {"file": ("books.txt", BytesIO(b"invalid content"), "text/plain")}

    response = await async_client.post(
        "/books/bulk-import", files=files, headers={"Authorization": f"Bearer {test_user_token.credentials}"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_bulk_import_unauthorized(async_client: AsyncClient):
    json_data = """[{"title": "Test", "author_name": "Test", "published_year": 2020, "genre": "Fiction"}]"""
    files = {"file": ("books.json", BytesIO(json_data.encode("utf-8")), "application/json")}

    response = await async_client.post("/books/bulk-import", files=files)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_books_pagination(async_client: AsyncClient, test_books_multiple):
    # Get first page
    response1 = await async_client.get("/books/?page=0&size=2")
    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    assert len(data1) == 2

    # Get second page
    response2 = await async_client.get("/books/?page=1&size=2")
    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()
    assert len(data2) >= 1

    # Verify no overlap
    ids1 = {book["id"] for book in data1}
    ids2 = {book["id"] for book in data2}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_params",
    [
        {"page": -1},
        {"size": 0},
        {"size": 200},
        {"year_min": 1700},
        {"year_max": 2100},
        {"sort_by": "invalid_field"},
        {"sort_order": "invalid_order"},
    ],
)
async def test_get_books_invalid_parameters(async_client: AsyncClient, invalid_params):
    response = await async_client.get("/books/", params=invalid_params)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
