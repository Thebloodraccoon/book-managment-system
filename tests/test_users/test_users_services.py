import pytest

from app.exceptions.user_exceptions import (
    UserEmailAlreadyExistsException,
    UserNotFoundException,
)
from app.users.schemas import UserCreate, UserUpdate
from app.users.services import UserService


@pytest.mark.parametrize("role", ["user", "admin"])
def test_create_user_success(db_session, role):
    service = UserService(db_session)
    data = UserCreate(
        email=f"new_{role}@example.com",
        password="securepassword",
        role=role,
    )
    user = service.create_user(data)
    assert user.email == f"new_{role}@example.com"
    assert user.role == role


def test_create_user_duplicate_email(db_session, test_user):
    service = UserService(db_session)
    data = UserCreate(
        email=test_user.email,
        password="12345678",
        role="user",
    )
    with pytest.raises(UserEmailAlreadyExistsException):
        service.create_user(data)


def test_get_user_by_id_success(db_session, test_user):
    service = UserService(db_session)
    user = service.get_user_by_id(test_user.id)
    assert user.email == test_user.email


def test_get_user_by_id_not_found(db_session):
    service = UserService(db_session)
    with pytest.raises(UserNotFoundException):
        service.get_user_by_id(99999)


def test_get_user_by_email_success(db_session, test_user):
    service = UserService(db_session)
    user = service.get_user_by_email(test_user.email)
    assert user.email == test_user.email


def test_get_user_by_email_not_found(db_session):
    service = UserService(db_session)
    with pytest.raises(UserNotFoundException):
        service.get_user_by_email("missing@example.com")


def test_get_all_users(db_session, test_user):
    service = UserService(db_session)
    users = service.get_all_users(page=0, size=10)
    assert isinstance(users, list)
    assert any(u.email == test_user.email for u in users)


@pytest.mark.parametrize(
    "update_data,expected",
    [
        (UserUpdate(email="updated@example.com"), {"email": "updated@example.com"}),
        (
            UserUpdate(email="both@example.com"),
            {"email": "both@example.com"},
        ),
    ],
)
def test_update_user_success(db_session, test_user, update_data, expected):
    service = UserService(db_session)
    updated = service.update_user(test_user.id, update_data)
    for field, value in expected.items():
        assert getattr(updated, field) == value


def test_update_user_not_found(db_session):
    service = UserService(db_session)
    data = UserUpdate(email="ghost@gmail.com")
    with pytest.raises(UserNotFoundException):
        service.update_user(99999, data)


def test_update_user_conflict_email(db_session, test_user, test_admin):
    service = UserService(db_session)
    data = UserUpdate(email=test_admin.email)
    with pytest.raises(UserEmailAlreadyExistsException):
        service.update_user(test_user.id, data)


def test_delete_user_success(db_session, test_user):
    service = UserService(db_session)
    result = service.delete_user(test_user.id)
    assert result is True


def test_delete_user_not_found(db_session):
    service = UserService(db_session)
    with pytest.raises(UserNotFoundException):
        service.delete_user(99999)
