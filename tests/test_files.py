from app.auth import register_user
from app.file_service import (
    create_file,
    read_file,
    write_file,
    delete_file,
    list_user_files,
)


def create_test_user(
    username="student",
    password="SecurePass123!",
):
    success, user_id = register_user(
        username,
        password,
    )

    assert success is True
    return user_id


def test_create_and_read_file():
    user_id = create_test_user()

    success, _ = create_file(
        user_id,
        "documents/test.txt",
        "Hello",
    )

    assert success is True

    success, content = read_file(
        user_id,
        "documents/test.txt",
    )

    assert success is True
    assert content == "Hello"


def test_modify_file():
    user_id = create_test_user()

    create_file(
        user_id,
        "test.txt",
        "old",
    )

    success, _ = write_file(
        user_id,
        "test.txt",
        "new",
    )

    assert success is True

    success, content = read_file(
        user_id,
        "test.txt",
    )

    assert success is True
    assert content == "new"


def test_delete_file():
    user_id = create_test_user()

    create_file(
        user_id,
        "test.txt",
        "data",
    )

    success, _ = delete_file(
        user_id,
        "test.txt",
    )

    assert success is True

    success, _ = read_file(
        user_id,
        "test.txt",
    )

    assert success is False


def test_list_user_files():
    user_id = create_test_user()

    create_file(
        user_id,
        "one.txt",
        "one",
    )

    create_file(
        user_id,
        "two.txt",
        "two",
    )

    files = list_user_files(user_id)

    locations = {
        file["location"]
        for file in files
    }

    assert "one.txt" in locations
    assert "two.txt" in locations


def test_user_cannot_read_another_users_file():
    first_user = create_test_user(
        "first_user",
        "Password123!",
    )

    second_user = create_test_user(
        "second_user",
        "Password456!",
    )

    create_file(
        first_user,
        "private.txt",
        "secret",
    )

    success, _ = read_file(
        second_user,
        "private.txt",
    )

    assert success is False
