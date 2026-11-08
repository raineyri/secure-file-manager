import sqlite3

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.database import get_connection


password_hasher = PasswordHasher()


def register_user(username: str, password: str):
    """Регистрация нового пользователя."""

    username = username.strip()

    if not username:
        return False, "Имя пользователя не может быть пустым."

    if len(username) < 3:
        return False, "Имя пользователя должно содержать минимум 3 символа."

    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов."

    password_hash = password_hasher.hash(password)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
                """,
                (username, password_hash),
            )

            user_id = cursor.lastrowid

        return True, user_id

    except sqlite3.IntegrityError:
        return False, "Пользователь с таким именем уже существует."


def authenticate_user(username: str, password: str):
    """Проверка имени пользователя и пароля."""

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, username, password_hash
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None:
        return False, None

    try:
        password_hasher.verify(user["password_hash"], password)

        # Если параметры Argon2 впоследствии были усилены,
        # хеш можно автоматически обновить.
        if password_hasher.check_needs_rehash(user["password_hash"]):
            new_hash = password_hasher.hash(password)

            with get_connection() as connection:
                connection.execute(
                    """
                    UPDATE users
                    SET password_hash = ?
                    WHERE id = ?
                    """,
                    (new_hash, user["id"]),
                )

        return True, {
            "id": user["id"],
            "username": user["username"],
        }

    except VerifyMismatchError:
        return False, None


def get_user_by_username(username: str):
    """Получение пользователя по имени."""

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, username, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
