from sqlalchemy.orm import Session

from app.auth.utils.pwd_utils import get_password_hash, verify_password
from app.models import User


def test_database_connection(db_session: Session):
    """Testing the database and the main operations with the user."""
    test_user = User(
        email="test@example.com",
        hashed_password=get_password_hash("Strong_password_hash"),
        role="user",
    )

    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    assert test_user.id is not None

    retrieved_user = db_session.query(User).filter_by(email="test@example.com").first()

    assert retrieved_user is not None
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.role == "user"
    assert verify_password("Strong_password_hash", retrieved_user.hashed_password)
