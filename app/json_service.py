import json

from app.file_service import create_file, read_file, write_file
from app.audit_service import log_operation


def save_json(user_id: int, relative_path: str, data):
    """Сохранение данных в JSON-файл."""

    try:
        json_content = json.dumps(
            data,
            ensure_ascii=False,
            indent=4,
        )
    except (TypeError, ValueError) as error:
        log_operation(
            user_id=user_id,
            operation_type="JSON_WRITE",
            result="DENIED",
            details=f"{relative_path}: {error}",
        )
        return False, f"Ошибка сериализации JSON: {error}"

    success, result = create_file(
        user_id,
        relative_path,
        json_content,
    )

    if success:
        return True, result

    if result == "Файл уже существует.":
        return write_file(
            user_id,
            relative_path,
            json_content,
        )

    return False, result


def read_json(user_id: int, relative_path: str):
    """Безопасное чтение JSON-файла."""

    success, content = read_file(
        user_id,
        relative_path,
    )

    if not success:
        return False, content

    try:
        data = json.loads(content)
        return True, data

    except json.JSONDecodeError as error:
        log_operation(
            user_id=user_id,
            operation_type="JSON_PARSE",
            result="DENIED",
            details=f"{relative_path}: {error}",
        )

        return False, f"Некорректный JSON: {error}"
