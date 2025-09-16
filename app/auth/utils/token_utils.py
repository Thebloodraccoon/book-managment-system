from datetime import datetime, timedelta, timezone

from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.exceptions.token_exceptions import InvalidTokenException, TokenBlacklistedException
from app.settings import settings


def create_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    """Create JWT token with specified type and expiration."""
    to_encode = data.copy()
    to_encode.update({"token_type": token_type})
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: dict):
    """Create access token with 30 minutes expiration."""
    return create_token(data, "access", timedelta(minutes=30))


def create_refresh_token(data: dict):
    """Create refresh token with 30 days expiration."""
    return create_token(data, "refresh", timedelta(days=30))


def create_temp_token(user_id: int) -> str:
    """Create temporary token for 2FA process with 5 minutes expiration."""
    payload = {"user_id": user_id}
    return create_token(payload, "temp", timedelta(minutes=5))


def decode_token(token: str) -> dict:
    """Decode JWT token and return payload."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise InvalidTokenException()


def get_token_expiration(token: str) -> datetime:
    """Get expiration time of JWT token."""
    payload = decode_token(token)
    exp_timestamp = float(payload.get("exp", "0.0"))
    return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)


def decode_temp_token(token: str) -> int:
    """Decode temporary token and return user_id."""
    try:
        payload = decode_token(token)
        if payload.get("token_type") != "temp":
            raise ValueError("Wrong token type")
        return payload["user_id"]
    except (ValueError, KeyError):
        raise InvalidTokenException()


async def add_token_to_blacklist(token: str, expire_time: datetime):
    """Add token to blacklist with expiration time."""
    async with settings.get_redis() as redis:
        token_ttl = int((expire_time - datetime.now(timezone.utc)).total_seconds())
        if token_ttl > 0:
            await redis.setex(f"blacklist:{token}", token_ttl, "blacklist_token")
            return True

        return False


async def is_token_blacklisted(token: str):
    """Check if token is blacklisted."""
    async with settings.get_redis() as redis:
        return await redis.exists(f"blacklist:{token}")


async def verify_token(token: HTTPAuthorizationCredentials | None, required_token_type: str) -> str:
    """Verify token and return email."""
    if token is None:
        raise InvalidTokenException()

    if await is_token_blacklisted(token.credentials):
        raise TokenBlacklistedException()

    payload = decode_token(token.credentials)
    email: str = payload.get("sub")  # type: ignore
    token_type: str = payload.get("token_type")  # type: ignore

    if email is None:
        raise InvalidTokenException()

    if token_type != required_token_type:
        raise InvalidTokenException()

    return email


async def verify_refresh_token(token_str: str) -> str:
    """Verify refresh token and return email."""
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_str)
    return await verify_token(token, "refresh")
