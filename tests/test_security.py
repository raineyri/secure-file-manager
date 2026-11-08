from app.auth import register_user
from app.file_service import (
    create_file,
    read_file,
)
from app.json_service import (
    save_json,
    read_json,
)
from app.xml_service import (
    save_xml,
    read_xml,
)


def create_test_user():
    success, user_id = register_user(
        "student",
        "SecurePass123!",
    )

    assert success is True
    return user_id


def test_path_traversal_is_blocked():
    user_id = create_test_user()

    success, message = read_file(
        user_id,
        "../../etc/passwd",
    )

    assert success is False
    assert "за пределы" in message


def test_absolute_path_is_blocked():
    user_id = create_test_user()

    success, message = create_file(
        user_id,
        "/tmp/hacked.txt",
        "test",
    )

    assert success is False
    assert "Абсолютные пути" in message


def test_json_save_and_read():
    user_id = create_test_user()

    data = {
        "username": "student",
        "role": "user",
        "active": True,
    }

    success, _ = save_json(
        user_id,
        "json/user.json",
        data,
    )

    assert success is True

    success, result = read_json(
        user_id,
        "json/user.json",
    )

    assert success is True
    assert result == data


def test_xml_save_and_read():
    user_id = create_test_user()

    data = {
        "username": "student",
        "role": "user",
    }

    success, _ = save_xml(
        user_id,
        "xml/user.xml",
        data,
    )

    assert success is True

    success, result = read_xml(
        user_id,
        "xml/user.xml",
    )

    assert success is True
    assert result["username"] == "student"
    assert result["role"] == "user"


def test_xxe_is_blocked():
    user_id = create_test_user()

    xxe = """<?xml version="1.0"?>
<!DOCTYPE data [
<!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>
    <value>&xxe;</value>
</data>
"""

    success, _ = create_file(
        user_id,
        "xml/unsafe.xml",
        xxe,
    )

    assert success is True

    success, result = read_xml(
        user_id,
        "xml/unsafe.xml",
    )

    assert success is False
    assert "EntitiesForbidden" in result
