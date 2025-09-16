from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.auth.services import AuthService
from app.auth.utils.token_utils import verify_token
from app.exceptions.auth_exceptions import AdminAccessException
from app.settings import settings
from app.settings.local import get_redis
from app.users.schemas import UserResponse
from app.users.services import UserService


async def redis_dependency() -> AsyncGenerator[Redis, None]:
    async with get_redis() as redis:
        yield redis


DatabaseDep = Annotated[Session, Depends(settings.get_db)]
RedisDep = Annotated[Redis, Depends(redis_dependency)]


def get_user_service(db: DatabaseDep) -> UserService:
    """Get User service instance."""
    return UserService(db)


def get_auth_service(db: DatabaseDep) -> AuthService:
    """Get Race service instance."""
    return AuthService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


security = HTTPBearer(
    scheme_name="JWT Bearer",
    description="JWT Bearer token for authentication",
    auto_error=False,
)
TokenDep = Annotated[HTTPAuthorizationCredentials | None, Depends(security)]


async def get_current_user(
    user_service: UserServiceDep,
    token: TokenDep,
) -> UserResponse:
    email = await verify_token(token, "access")
    return user_service.get_user_by_email(email)


def require_admin_access(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.role != "admin":
        raise AdminAccessException()

    return current_user


CurrentUserDep = Annotated[UserResponse, Depends(get_current_user)]
AdminUserDep = Annotated[UserResponse, Depends(require_admin_access)]
