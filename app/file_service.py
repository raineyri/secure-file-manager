from pathlib import Path
import shutil

import psutil

from app.config import STORAGE_DIR, init_directories
from app.database import get_connection
from app.audit_service import log_operation


class SecurityError(Exception):
    """Ошибка нарушения ограничений доступа к файловой системе."""


def _safe_path(relative_path: str):
    """
    Формирование безопасного пути внутри рабочей директории.

    Пользователь не может:
    - использовать абсолютный путь;
    - выйти за пределы STORAGE_DIR через ../.
    """

    init_directories()

    if not relative_path or not relative_path.strip():
        raise SecurityError(
            "Путь к файлу не может быть пустым."
        )

    user_path = Path(relative_path)

    if user_path.is_absolute():
        raise SecurityError(
            "Абсолютные пути запрещены."
        )

    storage_root = STORAGE_DIR.resolve()

    target_path = (
        storage_root / user_path
    ).resolve()

    if not target_path.is_relative_to(
        storage_root
    ):
        raise SecurityError(
            "Доступ за пределы рабочей директории запрещён."
        )

    return target_path


def get_storage_info():
    """
    Получение информации о файловой системе,
    в которой расположено хранилище приложения.
    """

    init_directories()

    usage = shutil.disk_usage(
        STORAGE_DIR
    )

    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
    }


def get_drives_info():
    """
    Получение сведений о доступных
    смонтированных файловых системах.

    Служебные loop-устройства и
    squashfs Snap исключаются из вывода.
    """

    drives = []
    seen_mountpoints = set()

    partitions = psutil.disk_partitions(
        all=False
    )

    for partition in partitions:
        if partition.device.startswith("/dev/loop"):
            continue

        if partition.fstype == "squashfs":
            continue

        if not partition.device.startswith("/dev/"):
            continue

        mountpoint = partition.mountpoint

        if mountpoint in seen_mountpoints:
            continue

        seen_mountpoints.add(
            mountpoint
        )

        try:
            usage = psutil.disk_usage(
                mountpoint
            )

        except (
            PermissionError,
            OSError,
        ):
            continue

        drives.append(
            {
                "device": partition.device,
                "mountpoint": mountpoint,
                "fstype": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            }
        )

    return drives


def _get_file_record(
    user_id: int,
    location: str,
):
    """
    Получение записи о файле,
    принадлежащем конкретному пользователю.
    """

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id,
                   filename,
                   size,
                   location,
                   owner_id
            FROM files
            WHERE owner_id = ?
              AND location = ?
            """,
            (
                user_id,
                location,
            ),
        ).fetchone()


def create_file(
    user_id: int,
    relative_path: str,
    content: str,
):
    """
    Создание текстового файла.
    """

    try:
        target_path = _safe_path(
            relative_path
        )

        if target_path.exists():
            raise FileExistsError(
                "Файл уже существует."
            )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path.write_text(
            content,
            encoding="utf-8",
        )

        size = target_path.stat().st_size

        location = str(
            target_path.relative_to(
                STORAGE_DIR.resolve()
            )
        )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO files (
                    filename,
                    size,
                    location,
                    owner_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    target_path.name,
                    size,
                    location,
                    user_id,
                ),
            )

            file_id = cursor.lastrowid

        log_operation(
            user_id=user_id,
            operation_type="CREATE",
            result="SUCCESS",
            file_id=file_id,
            details=(
                f"Создан файл: {location}"
            ),
        )

        return (
            True,
            f"Файл создан: {location}"
        )

    except (
        SecurityError,
        FileExistsError,
        OSError,
    ) as error:
        log_operation(
            user_id=user_id,
            operation_type="CREATE",
            result="DENIED",
            details=(
                f"{relative_path}: {error}"
            ),
        )

        return False, str(error)


def read_file(
    user_id: int,
    relative_path: str,
):
    """
    Чтение текстового файла.
    """

    try:
        target_path = _safe_path(
            relative_path
        )

        if not target_path.is_file():
            raise FileNotFoundError(
                "Файл не найден."
            )

        location = str(
            target_path.relative_to(
                STORAGE_DIR.resolve()
            )
        )

        file_record = _get_file_record(
            user_id,
            location,
        )

        if file_record is None:
            raise PermissionError(
                "Файл не принадлежит текущему пользователю."
            )

        content = target_path.read_text(
            encoding="utf-8"
        )

        log_operation(
            user_id=user_id,
            operation_type="READ",
            result="SUCCESS",
            file_id=file_record["id"],
            details=(
                f"Прочитан файл: {location}"
            ),
        )

        return True, content

    except (
        SecurityError,
        FileNotFoundError,
        PermissionError,
        UnicodeDecodeError,
        OSError,
    ) as error:
        log_operation(
            user_id=user_id,
            operation_type="READ",
            result="DENIED",
            details=(
                f"{relative_path}: {error}"
            ),
        )

        return False, str(error)


def write_file(
    user_id: int,
    relative_path: str,
    content: str,
):
    """
    Изменение существующего текстового файла.
    """

    try:
        target_path = _safe_path(
            relative_path
        )

        if not target_path.is_file():
            raise FileNotFoundError(
                "Файл не найден."
            )

        location = str(
            target_path.relative_to(
                STORAGE_DIR.resolve()
            )
        )

        file_record = _get_file_record(
            user_id,
            location,
        )

        if file_record is None:
            raise PermissionError(
                "Файл не принадлежит текущему пользователю."
            )

        target_path.write_text(
            content,
            encoding="utf-8",
        )

        new_size = (
            target_path.stat().st_size
        )

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE files
                SET size = ?
                WHERE id = ?
                """,
                (
                    new_size,
                    file_record["id"],
                ),
            )

        log_operation(
            user_id=user_id,
            operation_type="MODIFY",
            result="SUCCESS",
            file_id=file_record["id"],
            details=(
                f"Изменён файл: {location}"
            ),
        )

        return (
            True,
            "Файл успешно изменён."
        )

    except (
        SecurityError,
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        log_operation(
            user_id=user_id,
            operation_type="MODIFY",
            result="DENIED",
            details=(
                f"{relative_path}: {error}"
            ),
        )

        return False, str(error)


def delete_file(
    user_id: int,
    relative_path: str,
):
    """
    Удаление файла.
    """

    try:
        target_path = _safe_path(
            relative_path
        )

        if not target_path.is_file():
            raise FileNotFoundError(
                "Файл не найден."
            )

        location = str(
            target_path.relative_to(
                STORAGE_DIR.resolve()
            )
        )

        file_record = _get_file_record(
            user_id,
            location,
        )

        if file_record is None:
            raise PermissionError(
                "Файл не принадлежит текущему пользователю."
            )

        file_id = file_record["id"]

        log_operation(
            user_id=user_id,
            operation_type="DELETE",
            result="SUCCESS",
            file_id=file_id,
            details=(
                f"Удалён файл: {location}"
            ),
        )

        target_path.unlink()

        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM files
                WHERE id = ?
                """,
                (file_id,),
            )

        return (
            True,
            "Файл успешно удалён."
        )

    except (
        SecurityError,
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        log_operation(
            user_id=user_id,
            operation_type="DELETE",
            result="DENIED",
            details=(
                f"{relative_path}: {error}"
            ),
        )

        return False, str(error)


def list_user_files(user_id: int):
    """
    Получение списка файлов,
    принадлежащих пользователю.
    """

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id,
                   filename,
                   created_at,
                   size,
                   location
            FROM files
            WHERE owner_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
