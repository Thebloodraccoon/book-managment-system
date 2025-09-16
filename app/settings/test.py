from contextlib import asynccontextmanager

from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings.base import *  # noqa: F403

# Test Database settings
TEST_DATABASE_USER = "book_user"
TEST_DATABASE_PASSWORD = "test_secret"  # nosec B105
TEST_DATABASE_HOST = os.getenv("TEST_DATABASE_HOST", "localhost")
TEST_DATABASE_PORT = 5432
TEST_DATABASE_NAME = "book_test_db"
DATABASE_URL = (
    f"postgresql://{TEST_DATABASE_USER}:{TEST_DATABASE_PASSWORD}@{TEST_DATABASE_HOST}:{TEST_DATABASE_PORT}/"
    f"{TEST_DATABASE_NAME}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Test Redis settings
TEST_REDIS_HOST = os.getenv("TEST_REDIS_HOST", "localhost")
TEST_REDIS_PORT = 6379
TEST_REDIS_DB = 0


@asynccontextmanager
async def get_redis():
    redis_client = Redis(
        host=TEST_REDIS_HOST,
        port=TEST_REDIS_PORT,
        db=TEST_REDIS_DB,
        decode_responses=True,
    )
    try:
        yield redis_client
    finally:
        await redis_client.aclose()
