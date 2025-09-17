from datetime import datetime, timedelta, timezone
import re
import uuid

from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from jose import jwt
import pyotp
import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.utils.pwd_utils import get_password_hash
from app.main import app
from app.models import Author, Book, User
from app.models.book_model import GenreEnum
from app.settings import settings

test_engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    settings.Base.metadata.create_all(bind=test_engine)
    yield
    settings.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    try:
        for table in reversed(settings.Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session, redis_test):
    with TestClient(app, base_url="http://testserver/api") as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def redis_test():
    redis_client = Redis(
        host=settings.TEST_REDIS_HOST,
        port=settings.TEST_REDIS_PORT,
        db=settings.TEST_REDIS_DB,
        decode_responses=True,
    )
    await redis_client.flushdb()
    yield redis_client
    await redis_client.flushdb()
    await redis_client.aclose()


@pytest.fixture
def create_user(db_session):
    def _create_user(
        email="test@example.com",
        password="testpassword123",
        role="user",
    ):
        existing_user = db_session.query(User).filter_by(email=email).first()
        if existing_user:
            return existing_user

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=role,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        return user

    return _create_user


@pytest.fixture(
    params=[
        ("user@example.com", "user_password", "user"),
        ("admin@example.com", "admin_password", "admin"),
    ]
)
def user(request, create_user):
    email, password, role = request.param
    user = create_user(email=email, password=password, role=role)
    user._test_password = password
    return user


@pytest.fixture
def user_token(user, generate_jwt_token):
    return generate_jwt_token(user.email, token_type="access")


@pytest.fixture
def test_user(create_user):
    return create_user()


@pytest.fixture
def test_admin(create_user):
    return create_user(
        email="admin@admin.com",
        password="default_password",
        role="admin",
    )


def generate_test_otp_from_uri(otp_uri):
    secret_match = re.search(r"secret=([A-Z0-9]+)", otp_uri)
    if secret_match:
        secret = secret_match.group(1)
        totp = pyotp.TOTP(secret)
        return totp.now()
    raise Exception("Could not extract OTP secret from URI")


def generate_test_otp(secret):
    totp = pyotp.TOTP(secret)
    return totp.now()


def handle_2fa_flow(client, response, user=None):
    if "access_token" in response.json():
        return response.json()["access_token"]

    if "temp_token" in response.json():
        temp_token = response.json()["temp_token"]

        if "otp_uri" in response.json():
            otp_uri = response.json()["otp_uri"]
            otp_code = generate_test_otp_from_uri(otp_uri)
        else:
            if not user:
                raise ValueError("User object required for 2FA verification")
            otp_code = generate_test_otp(user.otp_secret)

        verify_response = client.post("/auth/2fa/verify", json={"otp_code": otp_code, "temp_token": temp_token})

        if verify_response.status_code == status.HTTP_200_OK:
            return verify_response.json()["access_token"]
        else:
            raise Exception(f"2FA verification failed: {verify_response.json()}")

    raise Exception("Unexpected login response format")


@pytest.fixture
def get_auth_token(client):
    def _get_auth_token(user, password):
        response = client.post("/auth/login", json={"email": user.email, "password": password})

        if response.status_code != status.HTTP_200_OK:
            raise Exception(f"Login failed: {response.json()}")

        access_token = handle_2fa_flow(client, response, user)
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)

    return _get_auth_token


@pytest.fixture
def test_user_token(get_auth_token, test_user):
    return get_auth_token(test_user, "testpassword123")


@pytest.fixture
def test_admin_token(get_auth_token, test_admin):
    return get_auth_token(test_admin, "default_password")


@pytest.fixture
def generate_jwt_token():
    def _generate_jwt_token(email: str, token_type: str, expires_in_minutes: int = 30):
        payload = {
            "sub": email,
            "jti": str(uuid.uuid4()),
            "token_type": token_type,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return _generate_jwt_token


@pytest.fixture
def create_author(db_session):
    def _create_author(name="Test Author"):
        existing_author = db_session.query(Author).filter_by(name=name).first()
        if existing_author:
            return existing_author

        author = Author(name=name)
        db_session.add(author)
        db_session.commit()
        db_session.refresh(author)
        return author

    return _create_author


@pytest.fixture
def create_book(db_session, create_author):
    def _create_book(title="Test Book", author_name="Test Author", published_year=2020, genre=GenreEnum.FICTION):
        author = create_author(name=author_name)

        existing_book = db_session.query(Book).filter_by(title=title, author_id=author.id).first()
        if existing_book:
            return existing_book

        book = Book(title=title, published_year=published_year, genre=genre, author_id=author.id)
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return _create_book


@pytest.fixture
def test_author(create_author):
    return create_author(name="J.K. Rowling")


@pytest.fixture
def test_book(create_book):
    return create_book(
        title="Harry Potter and the Philosopher's Stone",
        author_name="J.K. Rowling",
        published_year=1997,
        genre=GenreEnum.CHILDREN,
    )


@pytest.fixture
def test_books_multiple(create_book):
    """Create multiple books for testing pagination and filtering."""
    books = [
        create_book("1984", "George Orwell", 1949, GenreEnum.FICTION),
        create_book("Dune", "Frank Herbert", 1965, GenreEnum.SCIENCE),
        create_book("The Hobbit", "J.R.R. Tolkien", 1937, GenreEnum.FANTASY),
        create_book("Pride and Prejudice", "Jane Austen", 1813, GenreEnum.ROMANCE),
        create_book("The Art of War", "Sun Tzu", 1910, GenreEnum.HISTORY),
    ]
    return books


@pytest.fixture
def get_book_service_dependency():
    def override_get_book_service():
        from app.books.services import BookService
        from app.settings.test import get_db

        db = next(get_db())
        return BookService(db)

    return override_get_book_service
