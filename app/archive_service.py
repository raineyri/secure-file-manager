import stat
import zipfile
from pathlib import PurePosixPath

from app.config import STORAGE_DIR, init_directories
from app.database import get_connection
from app.file_service import _safe_path
from app.audit_service import log_operation


MAX_FILES = 100
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_TOTAL_SIZE = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100


def _register_file(user_id: int, file_path):
    """
    Регистрация файла в базе данных.

    Если запись о файле уже существует для данного пользователя,
    обновляются его размер и имя.
    """

    storage_root = STORAGE_DIR.resolve()
    resolved_path = file_path.resolve()

    location = str(
        resolved_path.relative_to(storage_root)
    )

    filename = resolved_path.name
    size = resolved_path.stat().st_size

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM files
            WHERE owner_id = ? AND location = ?
            """,
            (user_id, location),
        ).fetchone()

        if existing:
            connection.execute(
                """
                UPDATE files
                SET filename = ?, size = ?
                WHERE id = ?
                """,
                (
                    filename,
                    size,
                    existing["id"],
                ),
            )

            return existing["id"]

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
                filename,
                size,
                location,
                user_id,
            ),
        )

        return cursor.lastrowid


def _is_symlink(info: zipfile.ZipInfo):
    """
    Проверка, является ли элемент ZIP-архива
    символической ссылкой.
    """

    mode = info.external_attr >> 16

    return stat.S_ISLNK(mode)


def _validate_member(
    info: zipfile.ZipInfo,
    destination_root,
):
    """
    Проверка элемента ZIP-архива перед извлечением.

    Выполняется защита от:
    - ZipSlip;
    - символических ссылок;
    - чрезмерного размера файла;
    - аномального коэффициента сжатия.
    """

    normalized_name = info.filename.replace(
        "\\",
        "/",
    )

    member_path = PurePosixPath(
        normalized_name
    )

    if member_path.is_absolute():
        raise ValueError(
            f"Абсолютный путь в архиве запрещён: "
            f"{info.filename}"
        )

    if ".." in member_path.parts:
        raise ValueError(
            f"Обнаружен выход за пределы каталога: "
            f"{info.filename}"
        )

    if _is_symlink(info):
        raise ValueError(
            f"Символические ссылки запрещены: "
            f"{info.filename}"
        )

    if info.file_size > MAX_FILE_SIZE:
        raise ValueError(
            f"Превышен допустимый размер файла: "
            f"{info.filename}"
        )

    if (
        info.file_size > 0
        and info.compress_size == 0
    ):
        raise ValueError(
            f"Подозрительный размер сжатого файла: "
            f"{info.filename}"
        )

    if info.compress_size > 0:
        compression_ratio = (
            info.file_size
            / info.compress_size
        )

        if (
            compression_ratio
            > MAX_COMPRESSION_RATIO
        ):
            raise ValueError(
                "Слишком высокий коэффициент "
                f"сжатия для {info.filename}: "
                f"{compression_ratio:.1f}"
            )

    target_path = (
        destination_root
        / normalized_name
    ).resolve()

    if not target_path.is_relative_to(
        destination_root.resolve()
    ):
        raise ValueError(
            f"Обнаружен выход за пределы каталога: "
            f"{info.filename}"
        )

    return target_path


def create_zip(
    user_id: int,
    archive_relative_path: str,
    source_paths: list,
):
    """
    Создание ZIP-архива из файлов,
    принадлежащих текущему пользователю.
    """

    try:
        init_directories()

        if not source_paths:
            raise ValueError(
                "Не указаны файлы для архивации."
            )

        archive_path = _safe_path(
            archive_relative_path
        )

        if archive_path.suffix.lower() != ".zip":
            raise ValueError(
                "Архив должен иметь расширение .zip."
            )

        if archive_path.exists():
            raise FileExistsError(
                "ZIP-архив уже существует."
            )

        validated_sources = []

        for relative_path in source_paths:
            source_path = _safe_path(
                relative_path
            )

            if not source_path.is_file():
                raise FileNotFoundError(
                    f"Файл не найден: "
                    f"{relative_path}"
                )

            location = str(
                source_path.relative_to(
                    STORAGE_DIR.resolve()
                )
            )

            with get_connection() as connection:
                file_record = connection.execute(
                    """
                    SELECT id
                    FROM files
                    WHERE owner_id = ?
                      AND location = ?
                    """,
                    (
                        user_id,
                        location,
                    ),
                ).fetchone()

            if file_record is None:
                raise PermissionError(
                    "Нет доступа к файлу: "
                    f"{relative_path}"
                )

            validated_sources.append(
                source_path
            )

        archive_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for source_path in validated_sources:
                archive_name = str(
                    source_path.relative_to(
                        STORAGE_DIR.resolve()
                    )
                )

                archive.write(
                    source_path,
                    arcname=archive_name,
                )

        archive_id = _register_file(
            user_id,
            archive_path,
        )

        log_operation(
            user_id=user_id,
            operation_type="ZIP_CREATE",
            result="SUCCESS",
            file_id=archive_id,
            details=(
                f"Создан архив: "
                f"{archive_relative_path}; "
                f"файлов: "
                f"{len(validated_sources)}"
            ),
        )

        return (
            True,
            "ZIP-архив успешно создан."
        )

    except Exception as error:
        log_operation(
            user_id=user_id,
            operation_type="ZIP_CREATE",
            result="DENIED",
            details=(
                f"{archive_relative_path}: "
                f"{error}"
            ),
        )

        return False, str(error)


def extract_zip(
    user_id: int,
    archive_relative_path: str,
    destination_relative_path: str,
):
    """
    Безопасное извлечение ZIP-архива.

    Перед распаковкой проверяются:
    - принадлежность архива пользователю;
    - количество файлов;
    - суммарный размер;
    - размер каждого файла;
    - коэффициент сжатия;
    - попытки ZipSlip;
    - символические ссылки.
    """

    try:
        init_directories()

        archive_path = _safe_path(
            archive_relative_path
        )

        destination_root = _safe_path(
            destination_relative_path
        )

        if not archive_path.is_file():
            raise FileNotFoundError(
                "ZIP-архив не найден."
            )

        # Дополнительная проверка:
        # архив должен принадлежать
        # текущему пользователю.
        archive_location = str(
            archive_path.relative_to(
                STORAGE_DIR.resolve()
            )
        )

        with get_connection() as connection:
            archive_record = connection.execute(
                """
                SELECT id
                FROM files
                WHERE owner_id = ?
                  AND location = ?
                """,
                (
                    user_id,
                    archive_location,
                ),
            ).fetchone()

        if archive_record is None:
            raise PermissionError(
                "ZIP-архив не принадлежит "
                "текущему пользователю."
            )

        destination_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:
            members = archive.infolist()

            if len(members) > MAX_FILES:
                raise ValueError(
                    "Превышено допустимое "
                    "количество файлов в архиве."
                )

            total_declared_size = sum(
                info.file_size
                for info in members
                if not info.is_dir()
            )

            if (
                total_declared_size
                > MAX_TOTAL_SIZE
            ):
                raise ValueError(
                    "Превышен допустимый "
                    "суммарный размер архива."
                )

            validated_members = []

            # Сначала проверяются все элементы.
            # Извлечение начинается только после
            # успешного завершения проверок.
            for info in members:
                target_path = _validate_member(
                    info,
                    destination_root,
                )

                validated_members.append(
                    (
                        info,
                        target_path,
                    )
                )

            total_extracted_size = 0
            extracted_files = 0

            for info, target_path in validated_members:
                if info.is_dir():
                    target_path.mkdir(
                        parents=True,
                        exist_ok=True,
                    )
                    continue

                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                current_file_size = 0

                with archive.open(
                    info,
                    "r",
                ) as source:
                    with open(
                        target_path,
                        "wb",
                    ) as destination:
                        while True:
                            chunk = source.read(
                                65536
                            )

                            if not chunk:
                                break

                            current_file_size += len(
                                chunk
                            )

                            total_extracted_size += len(
                                chunk
                            )

                            if (
                                current_file_size
                                > MAX_FILE_SIZE
                            ):
                                raise ValueError(
                                    "Превышен допустимый "
                                    "размер извлекаемого "
                                    f"файла: {info.filename}"
                                )

                            if (
                                total_extracted_size
                                > MAX_TOTAL_SIZE
                            ):
                                raise ValueError(
                                    "Превышен допустимый "
                                    "суммарный размер "
                                    "извлекаемых данных."
                                )

                            destination.write(
                                chunk
                            )

                _register_file(
                    user_id,
                    target_path,
                )

                extracted_files += 1

        log_operation(
            user_id=user_id,
            operation_type="ZIP_EXTRACT",
            result="SUCCESS",
            file_id=archive_record["id"],
            details=(
                f"Архив "
                f"{archive_relative_path} "
                f"распакован в "
                f"{destination_relative_path}; "
                f"файлов: {extracted_files}"
            ),
        )

        return (
            True,
            "Архив успешно распакован. "
            f"Файлов: {extracted_files}"
        )

    except (
        zipfile.BadZipFile,
        ValueError,
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as error:
        log_operation(
            user_id=user_id,
            operation_type="ZIP_EXTRACT",
            result="DENIED",
            details=(
                f"{archive_relative_path}: "
                f"{error}"
            ),
        )

        return False, str(error)
