import pyotp

from app.settings import settings

SECRET = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM


def generate_otp_secret() -> str:
    return pyotp.random_base32()


def generate_otp_uri(email: str, secret: str, issuer: str = "Book managment system") -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_otp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
