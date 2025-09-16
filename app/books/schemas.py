from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.book_model import GenreEnum


class BookBase(BaseModel):
    title: str
    published_year: int
    genre: GenreEnum

    @field_validator("title")
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Title must be a non-empty string")
        return v.strip()

    @field_validator("published_year")
    def validate_published_year(cls, v):
        current_year = datetime.now().year
        if v < 1800 or v > current_year:
            raise ValueError(f"Published year must be between 1800 and {current_year}")
        return v


class BookCreate(BookBase):
    author_name: str

    @field_validator("author_name")
    def validate_author_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Author name must be a non-empty string")
        return v.strip()


class BookUpdate(BaseModel):
    title: str | None = None
    published_year: int | None = None
    genre: GenreEnum | None = None
    author_name: str | None = None

    @field_validator("title")
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Title must be a non-empty string")
        return v.strip() if v else v

    @field_validator("published_year")
    def validate_published_year(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < 1800 or v > current_year:
                raise ValueError(f"Published year must be between 1800 and {current_year}")
        return v

    @field_validator("author_name")
    def validate_author_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Author name must be a non-empty string")
        return v.strip() if v else v


class AuthorResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookResponse(BookBase):
    id: int
    author_id: int
    author: AuthorResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkImportResponse(BaseModel):
    total_processed: int
    successful_imports: int
    failed_imports: int
    errors: list[str]


class BookImportData(BaseModel):
    title: str
    author_name: str
    published_year: int
    genre: str

    @field_validator("genre")
    def validate_genre(cls, v):
        try:
            return GenreEnum(v)
        except ValueError:
            valid_genres = [g.value for g in GenreEnum]
            raise ValueError(f"Invalid genre. Must be one of: {', '.join(valid_genres)}")


class AuthorCreate(BaseModel):
    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Author name must be a non-empty string")
        return v.strip()


class AuthorUpdate(BaseModel):
    name: str | None = None

    @field_validator("name")
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Author name must be a non-empty string")
        return v.strip() if v else v
