from app.auth import (
    register_user,
    authenticate_user,
)
from app.database import get_connection


def test_register_user():
    success, user_id = register_user(
        "student",
        "SecurePass123!",
    )

    assert success is True
    assert isinstance(user_id, int)


def test_duplicate_username_is_rejected():
    register_user(
        "student",
        "SecurePass123!",
    )

    success, message = register_user(
        "student",
        "AnotherPass123!",
    )

    assert success is False
    assert "уже существует" in message


def test_correct_password():
    register_user(
        "student",
        "SecurePass123!",
    )

    success, user = authenticate_user(
        "student",
        "SecurePass123!",
    )

    assert success is True
    assert user["username"] == "student"


def test_wrong_password():
    register_user(
        "student",
        "SecurePass123!",
    )

    success, user = authenticate_user(
        "student",
        "wrong-password",
    )

    assert success is False
    assert user is None


def test_password_is_not_stored_in_plaintext():
    register_user(
        "student",
        "SecurePass123!",
    )

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE username = ?
            """,
            ("student",),
        ).fetchone()

    assert user is not None
    assert user["password_hash"] != "SecurePass123!"
    assert user["password_hash"].startswith("$argon2")


def test_sql_injection_login_is_rejected():
    register_user(
        "student",
        "SecurePass123!",
    )

    success, user = authenticate_user(
        "' OR 1=1 --",
        "anything",
    )

    assert success is False
    assert user is None
