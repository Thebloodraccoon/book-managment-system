from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.exceptions.user_exceptions import InvalidEmailException, InvalidPasswordException


class UserBase(BaseModel):
    role: Literal["user", "admin"]  # type: ignore
    email: str

    @field_validator("email")
    def validate_email(cls, email):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise InvalidEmailException()
        return email


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    def validate_password(cls, password):
        if len(password) < 8:
            raise InvalidPasswordException("Password must be at least 8 characters long")
        return password


class UserUpdate(BaseModel):
    email: str | None = None
    role: Literal["user", "admin"] | None = None

    @field_validator("email")
    def validate_email(cls, email):
        if email is not None and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise InvalidEmailException()
        return email


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
