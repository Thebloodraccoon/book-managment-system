from fastapi import APIRouter, File, Query, UploadFile, status

from app.books.schemas import BookCreate, BookResponse, BookUpdate, BulkImportResponse
from app.core.dependencies import BookServiceDep, CurrentUserDep

router = APIRouter()


@router.get("/", response_model=list[BookResponse])
def get_books(
    book_service: BookServiceDep,
    page: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
    title: str | None = Query(None),
    author: str | None = Query(None),
    genre: str | None = Query(None),
    year_min: int | None = Query(None, ge=1800),
    year_max: int | None = Query(None, le=2025),
    sort_by: str = Query("title", regex="^(title|published_year|author)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
):
    """Get all books with filtering, pagination, and sorting."""
    return book_service.get_books(page, size, title, author, genre, year_min, year_max, sort_by, sort_order)


@router.get("/{book_id}", response_model=BookResponse)
def get_book_by_id(book_id: int, book_service: BookServiceDep):
    """Get book by ID."""
    return book_service.get_book_by_id(book_id)


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(book_data: BookCreate, book_service: BookServiceDep, _: CurrentUserDep):
    """Create a new book."""
    return book_service.create_book(book_data)


@router.put("/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_data: BookUpdate, book_service: BookServiceDep, _: CurrentUserDep):
    """Update book by ID."""
    return book_service.update_book(book_id, book_data)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, book_service: BookServiceDep, _: CurrentUserDep):
    """Delete book by ID."""
    book_service.delete_book(book_id)


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import_books(
    book_service: BookServiceDep,
    _: CurrentUserDep,
    file: UploadFile = File(...),
):
    """Bulk import books from JSON or CSV file."""
    return await book_service.bulk_import_books(file)
