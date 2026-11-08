import zipfile

import app.archive_service as archive_service

from app.auth import register_user
from app.file_service import create_file
from app.archive_service import (
    create_zip,
    extract_zip,
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


def test_create_and_extract_zip():
    user_id = create_test_user()

    create_file(
        user_id,
        "documents/test.txt",
        "Hello ZIP",
    )

    success, _ = create_zip(
        user_id,
        "archives/test.zip",
        ["documents/test.txt"],
    )

    assert success is True

    success, message = extract_zip(
        user_id,
        "archives/test.zip",
        "restored",
    )

    assert success is True
    assert "успешно" in message.lower()

    restored_file = (
        archive_service.STORAGE_DIR
        / "restored"
        / "documents"
        / "test.txt"
    )

    assert restored_file.exists()
    assert restored_file.read_text(
        encoding="utf-8"
    ) == "Hello ZIP"


def test_zipslip_is_blocked():
    user_id = create_test_user()

    archive_path = (
        archive_service.STORAGE_DIR
        / "archives"
        / "unsafe.zip"
    )

    archive_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with zipfile.ZipFile(
        archive_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "../../outside.txt",
            "THIS MUST NOT BE EXTRACTED",
        )

    archive_service._register_file(
        user_id,
        archive_path,
    )

    success, message = extract_zip(
        user_id,
        "archives/unsafe.zip",
        "output",
    )

    assert success is False
    assert "за пределы" in message

    outside_file = (
        archive_service.STORAGE_DIR.parent
        / "outside.txt"
    )

    assert not outside_file.exists()


def test_high_compression_ratio_is_blocked():
    user_id = create_test_user()

    archive_path = (
        archive_service.STORAGE_DIR
        / "archives"
        / "ratio.zip"
    )

    archive_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with zipfile.ZipFile(
        archive_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "large.txt",
            b"A" * 1_000_000,
        )

    archive_service._register_file(
        user_id,
        archive_path,
    )

    success, message = extract_zip(
        user_id,
        "archives/ratio.zip",
        "output",
    )

    assert success is False
    assert "коэффициент сжатия" in message


def test_user_cannot_extract_another_users_archive():
    owner_id = create_test_user(
        "archive_owner",
        "OwnerPass123!",
    )

    other_user_id = create_test_user(
        "other_user",
        "OtherPass123!",
    )

    create_file(
        owner_id,
        "documents/secret.txt",
        "secret",
    )

    success, _ = create_zip(
        owner_id,
        "archives/private.zip",
        ["documents/secret.txt"],
    )

    assert success is True

    success, message = extract_zip(
        other_user_id,
        "archives/private.zip",
        "stolen",
    )

    assert success is False
    assert "не принадлежит" in message
