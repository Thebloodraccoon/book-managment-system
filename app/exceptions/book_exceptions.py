from fastapi import HTTPException, status


class BookNotFoundException(HTTPException):
    def __init__(self, book_id: int | None = None, title: str | None = None):
        detail = "Book not found"

        if book_id:
            detail = f"Book with ID {book_id} not found"

        if title:
            detail = f"Book with title '{title}' not found"

        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BookAlreadyExistsException(HTTPException):
    def __init__(self, title: str, author: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book '{title}' by {author} already exists"
        )


class InvalidFileFormatException(HTTPException):
    def __init__(self, filename: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format for '{filename}'. Only CSV and JSON files are supported"
        )


class EmptyFileException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty or contains no valid data"
        )
