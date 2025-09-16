from datetime import datetime

from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.models import User


class UserRepository(BaseRepository[User]):
    """Repository for the essence of User."""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        """Obtaining a user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def update_otp_secret(self, user: User, otp_secret: str) -> User:
        """Update user's OTP secret."""
        user.otp_secret = otp_secret  # type: ignore
        self.db.commit()
        self.db.refresh(user)
        return user

    def enable_2fa(self, user: User) -> User:
        """Enable 2FA for user."""
        user.is_2fa_enabled = True  # type: ignore
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_last_login(self, user: User) -> User:
        """Update user's last login timestamp."""
        user.last_login = datetime.now()  # type: ignore
        self.db.commit()
        self.db.refresh(user)
        return user

    def setup_2fa(self, user: User, otp_secret: str) -> User:
        """Setup 2FA for user (set secret but don't enable yet)."""
        user.otp_secret = otp_secret  # type: ignore
        self.db.commit()
        self.db.refresh(user)
        return user

    def complete_2fa_setup(self, user: User) -> User:
        """Complete 2FA setup (enable 2FA and update last login)."""
        user.is_2fa_enabled = True  # type: ignore
        return self.update_last_login(user)
