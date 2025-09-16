from fastapi import Response
from sqlalchemy.orm import Session

from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LoginResponseUnion,
    LogoutResponse,
    RefreshResponse,
    TwoFARequiredResponse,
    TwoFASetupResponse,
    TwoFAVerifyRequest,
)
from app.auth.utils.pwd_utils import verify_password
from app.auth.utils.token_utils import (
    add_token_to_blacklist,
    create_access_token,
    create_refresh_token,
    create_temp_token,
    decode_temp_token,
    get_token_expiration,
    verify_refresh_token,
)
from app.auth.utils.twofa_utils import generate_otp_secret, generate_otp_uri, verify_otp_code
from app.exceptions.auth_exceptions import InvalidCodeException, InvalidCredentialsException
from app.settings import settings
from app.users.repository import UserRepository


def create_login_response(user, response: Response) -> LoginResponse:
    """Create login response with tokens and cookies."""
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=30 * 24 * 60 * 60,
    )

    return LoginResponse(access_token=access_token)


class AuthService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def login(self, request: LoginRequest, response: Response) -> LoginResponseUnion:
        """Handle login with 2FA support."""
        user = self.user_repo.get_by_email(request.email)

        if not user or not verify_password(request.password, str(user.hashed_password)):
            raise InvalidCredentialsException()

        if user.email == settings.ADMIN_LOGIN:
            updated_user = self.user_repo.update_last_login(user)
            return create_login_response(updated_user, response)

        if not user.is_2fa_enabled:
            if not user.otp_secret:
                otp_secret = generate_otp_secret()
                user = self.user_repo.setup_2fa(user, otp_secret)

            return TwoFASetupResponse(
                otp_uri=generate_otp_uri(str(user.email), str(user.otp_secret)),
                temp_token=create_temp_token(int(user.id)),
            )

        return TwoFARequiredResponse(temp_token=create_temp_token(int(user.id)))

    def verify_2fa(self, request: TwoFAVerifyRequest, response: Response) -> LoginResponse:
        """Verify 2FA code and complete login."""
        user_id = decode_temp_token(request.temp_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise InvalidCredentialsException()

        if not verify_otp_code(str(user.otp_secret), request.otp_code):
            raise InvalidCodeException()

        if not user.is_2fa_enabled:
            updated_user = self.user_repo.complete_2fa_setup(user)
        else:
            updated_user = self.user_repo.update_last_login(user)
        return create_login_response(updated_user, response)

    async def refresh_tokens(self, refresh_token: str) -> RefreshResponse:
        email = await verify_refresh_token(refresh_token)
        user = self.user_repo.get_by_email(email)

        if not user:
            raise InvalidCredentialsException()

        new_access_token = create_access_token(data={"sub": user.email})
        return RefreshResponse(access_token=new_access_token)

    @classmethod
    async def logout_user(cls, access_token: str, refresh_token: str) -> LogoutResponse:
        exp = get_token_expiration(access_token)

        blacklist_access = await add_token_to_blacklist(access_token, exp)
        if refresh_token:
            await add_token_to_blacklist(refresh_token, exp)

        if blacklist_access:
            return LogoutResponse(detail="Successful logout")

        return LogoutResponse(detail="Token is already expired")
