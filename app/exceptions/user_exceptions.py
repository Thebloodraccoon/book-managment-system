from fastapi import HTTPException, status


class UserNotFoundException(HTTPException):
    def __init__(self, user_id: int | None = None, email: str | None = None):
        detail = "404 User is not found"

        if user_id:
            detail = f"User with ID {user_id} is not found."

        if email:
            detail = f"User with email {email} is not found."

        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InvalidEmailException(HTTPException):
    def __init__(self, message: str = "Invalid email address"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )


class InvalidPasswordException(HTTPException):
    def __init__(self, message: str = "Invalid password"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )


class UserEmailAlreadyExistsException(HTTPException):
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {email} already exists.",
        )
