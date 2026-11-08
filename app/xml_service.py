import xml.etree.ElementTree as ET

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from app.file_service import create_file, read_file, write_file
from app.audit_service import log_operation


def save_xml(user_id: int, relative_path: str, data: dict):
    """Сохранение словаря в XML-файл."""

    if not isinstance(data, dict):
        return False, "Для записи XML ожидается словарь."

    root = ET.Element("data")

    for key, value in data.items():
        element = ET.SubElement(root, str(key))
        element.text = str(value)

    xml_content = ET.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
    )

    xml_content = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_content

    success, result = create_file(
        user_id,
        relative_path,
        xml_content,
    )

    if success:
        return True, result

    if result == "Файл уже существует.":
        return write_file(
            user_id,
            relative_path,
            xml_content,
        )

    return False, result


def read_xml(user_id: int, relative_path: str):
    """Чтение XML с защитой от опасных сущностей."""

    success, content = read_file(
        user_id,
        relative_path,
    )

    if not success:
        return False, content

    try:
        root = SafeET.fromstring(content)

        result = {}

        for child in root:
            result[child.tag] = child.text

        return True, result

    except DefusedXmlException as error:
        log_operation(
            user_id=user_id,
            operation_type="XML_PARSE",
            result="DENIED",
            details=(
                f"{relative_path}: "
                f"заблокирована потенциально опасная XML-конструкция"
            ),
        )

        return False, (
            "Обработка XML заблокирована механизмом безопасности: "
            f"{type(error).__name__}"
        )

    except ET.ParseError as error:
        log_operation(
            user_id=user_id,
            operation_type="XML_PARSE",
            result="DENIED",
            details=f"{relative_path}: {error}",
        )

        return False, f"Некорректный XML: {error}"
