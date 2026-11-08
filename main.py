from getpass import getpass

from app.auth import (
    register_user,
    authenticate_user,
)
from app.database import init_database
from app.file_service import (
    get_drives_info,
    list_user_files,
    create_file,
    read_file,
    write_file,
    delete_file,
)
from app.json_service import (
    save_json,
    read_json,
)
from app.xml_service import (
    save_xml,
    read_xml,
)
from app.archive_service import (
    create_zip,
    extract_zip,
)
from app.audit_service import (
    get_user_operations,
)


def print_separator():
    print("=" * 60)


def format_size(size_bytes: int):
    """Преобразование размера в удобный формат."""

    size = float(size_bytes)

    for unit in (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ):
        if size < 1024:
            return (
                f"{size:.2f} {unit}"
            )

        size /= 1024

    return f"{size:.2f} PB"


def show_drives_info():
    """
    Вывод сведений о доступных
    файловых системах.
    """

    drives = get_drives_info()

    if not drives:
        print(
            "\nНе удалось получить "
            "сведения о файловых системах."
        )
        return

    print(
        "\nДоступные файловые системы:"
    )

    print_separator()

    for drive in drives:
        print(
            f"Устройство:       "
            f"{drive['device']}"
        )

        print(
            f"Точка монтирования: "
            f"{drive['mountpoint']}"
        )

        print(
            f"Тип файловой системы: "
            f"{drive['fstype']}"
        )

        print(
            f"Общий объём:      "
            f"{format_size(drive['total'])}"
        )

        print(
            f"Использовано:     "
            f"{format_size(drive['used'])}"
        )

        print(
            f"Свободно:         "
            f"{format_size(drive['free'])}"
        )

        print(
            f"Использовано, %:  "
            f"{drive['percent']}%"
        )

        print("-" * 60)


def show_files(user_id: int):
    files = list_user_files(
        user_id
    )

    if not files:
        print(
            "\nФайлы отсутствуют."
        )
        return

    print(
        "\nФайлы пользователя:"
    )

    print_separator()

    for file in files:
        print(
            f"ID: {file['id']} | "
            f"Имя: {file['filename']} | "
            f"Размер: {file['size']} байт | "
            f"Путь: {file['location']}"
        )

    print_separator()


def create_text_file(user_id: int):
    path = input(
        "Введите относительный "
        "путь к файлу: "
    ).strip()

    content = input(
        "Введите содержимое файла: "
    )

    success, message = create_file(
        user_id,
        path,
        content,
    )

    print(message)


def read_text_file(user_id: int):
    path = input(
        "Введите путь к файлу: "
    ).strip()

    success, result = read_file(
        user_id,
        path,
    )

    if success:
        print(
            "\nСодержимое файла:"
        )

        print_separator()
        print(result)
        print_separator()

    else:
        print(
            f"Ошибка: {result}"
        )


def modify_text_file(user_id: int):
    path = input(
        "Введите путь к файлу: "
    ).strip()

    content = input(
        "Введите новое содержимое: "
    )

    success, message = write_file(
        user_id,
        path,
        content,
    )

    print(message)


def remove_file(user_id: int):
    path = input(
        "Введите путь к "
        "удаляемому файлу: "
    ).strip()

    confirmation = input(
        f"Удалить файл '{path}'? "
        "[y/N]: "
    ).strip().lower()

    if confirmation != "y":
        print(
            "Удаление отменено."
        )
        return

    success, message = delete_file(
        user_id,
        path,
    )

    print(message)


def json_menu(user_id: int):
    while True:
        print(
            "\n--- Работа с JSON ---"
        )

        print("1. Записать JSON")
        print("2. Прочитать JSON")
        print("0. Назад")

        choice = input(
            "Выберите действие: "
        ).strip()

        if choice == "1":
            path = input(
                "Путь к JSON-файлу: "
            ).strip()

            key = input(
                "Ключ: "
            ).strip()

            value = input(
                "Значение: "
            ).strip()

            success, message = save_json(
                user_id,
                path,
                {
                    key: value,
                },
            )

            print(message)

        elif choice == "2":
            path = input(
                "Путь к JSON-файлу: "
            ).strip()

            success, result = read_json(
                user_id,
                path,
            )

            if success:
                print("JSON:")
                print(result)

            else:
                print(
                    f"Ошибка: {result}"
                )

        elif choice == "0":
            break

        else:
            print(
                "Некорректный пункт меню."
            )


def xml_menu(user_id: int):
    while True:
        print(
            "\n--- Работа с XML ---"
        )

        print("1. Записать XML")
        print("2. Прочитать XML")
        print("0. Назад")

        choice = input(
            "Выберите действие: "
        ).strip()

        if choice == "1":
            path = input(
                "Путь к XML-файлу: "
            ).strip()

            key = input(
                "Имя элемента: "
            ).strip()

            value = input(
                "Значение: "
            ).strip()

            success, message = save_xml(
                user_id,
                path,
                {
                    key: value,
                },
            )

            print(message)

        elif choice == "2":
            path = input(
                "Путь к XML-файлу: "
            ).strip()

            success, result = read_xml(
                user_id,
                path,
            )

            if success:
                print("XML:")
                print(result)

            else:
                print(
                    f"Ошибка: {result}"
                )

        elif choice == "0":
            break

        else:
            print(
                "Некорректный пункт меню."
            )


def create_archive_menu(user_id: int):
    archive_path = input(
        "Путь к создаваемому "
        "ZIP-архиву: "
    ).strip()

    print(
        "Введите пути к файлам "
        "через запятую."
    )

    source_input = input(
        "Файлы: "
    ).strip()

    source_paths = [
        item.strip()
        for item
        in source_input.split(",")
        if item.strip()
    ]

    success, message = create_zip(
        user_id,
        archive_path,
        source_paths,
    )

    print(message)


def extract_archive_menu(
    user_id: int,
):
    archive_path = input(
        "Путь к ZIP-архиву: "
    ).strip()

    destination = input(
        "Каталог для распаковки: "
    ).strip()

    success, message = extract_zip(
        user_id,
        archive_path,
        destination,
    )

    print(message)


def show_audit_log(user_id: int):
    operations = get_user_operations(
        user_id
    )

    if not operations:
        print(
            "\nЖурнал операций пуст."
        )
        return

    print(
        "\nЖурнал операций:"
    )

    print_separator()

    for operation in operations:
        print(
            f"[{operation['timestamp']}] "
            f"{operation['operation_type']} | "
            f"{operation['result']}"
        )

        if operation["details"]:
            print(
                f"    "
                f"{operation['details']}"
            )

    print_separator()


def user_menu(user: dict):
    user_id = user["id"]
    username = user["username"]

    while True:
        print()
        print_separator()

        print(
            "SECURE FILE MANAGER"
        )

        print(
            f"Пользователь: "
            f"{username}"
        )

        print_separator()

        print(
            "1. Информация о дисках "
            "и файловых системах"
        )

        print(
            "2. Список файлов"
        )

        print(
            "3. Создать текстовый файл"
        )

        print(
            "4. Прочитать файл"
        )

        print(
            "5. Изменить файл"
        )

        print(
            "6. Удалить файл"
        )

        print(
            "7. Работа с JSON"
        )

        print(
            "8. Работа с XML"
        )

        print(
            "9. Создать ZIP-архив"
        )

        print(
            "10. Распаковать ZIP-архив"
        )

        print(
            "11. Просмотреть журнал операций"
        )

        print(
            "0. Выйти из учётной записи"
        )

        choice = input(
            "\nВыберите действие: "
        ).strip()

        if choice == "1":
            show_drives_info()

        elif choice == "2":
            show_files(
                user_id
            )

        elif choice == "3":
            create_text_file(
                user_id
            )

        elif choice == "4":
            read_text_file(
                user_id
            )

        elif choice == "5":
            modify_text_file(
                user_id
            )

        elif choice == "6":
            remove_file(
                user_id
            )

        elif choice == "7":
            json_menu(
                user_id
            )

        elif choice == "8":
            xml_menu(
                user_id
            )

        elif choice == "9":
            create_archive_menu(
                user_id
            )

        elif choice == "10":
            extract_archive_menu(
                user_id
            )

        elif choice == "11":
            show_audit_log(
                user_id
            )

        elif choice == "0":
            print(
                "Выход из учётной записи."
            )
            break

        else:
            print(
                "Некорректный пункт меню."
            )


def authentication_menu():
    while True:
        print()
        print_separator()

        print(
            "SECURE FILE MANAGER"
        )

        print_separator()

        print("1. Регистрация")
        print("2. Вход")
        print(
            "0. Завершить программу"
        )

        choice = input(
            "\nВыберите действие: "
        ).strip()

        if choice == "1":
            username = input(
                "Имя пользователя: "
            ).strip()

            password = getpass(
                "Пароль: "
            )

            confirmation = getpass(
                "Повторите пароль: "
            )

            if password != confirmation:
                print(
                    "Пароли не совпадают."
                )
                continue

            success, result = register_user(
                username,
                password,
            )

            if success:
                print(
                    "Пользователь успешно "
                    "зарегистрирован."
                )

            else:
                print(
                    f"Ошибка регистрации: "
                    f"{result}"
                )

        elif choice == "2":
            username = input(
                "Имя пользователя: "
            ).strip()

            password = getpass(
                "Пароль: "
            )

            success, user = authenticate_user(
                username,
                password,
            )

            if success:
                print(
                    "Аутентификация "
                    "выполнена успешно."
                )

                user_menu(user)

            else:
                print(
                    "Неверное имя пользователя "
                    "или пароль."
                )

        elif choice == "0":
            print(
                "Завершение программы."
            )
            break

        else:
            print(
                "Некорректный пункт меню."
            )


def main():
    init_database()
    authentication_menu()


if __name__ == "__main__":
    main()
