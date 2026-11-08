import sqlite3

from app.config import DATABASE_PATH, init_directories


def get_connection():
    """Создание подключения к базе данных SQLite."""
    init_directories()

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    # SQLite требует отдельного включения контроля внешних ключей
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_database():
    """Создание таблиц базы данных при первом запуске."""

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                size INTEGER NOT NULL DEFAULT 0,
                location TEXT NOT NULL,
                owner_id INTEGER NOT NULL,

                FOREIGN KEY (owner_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                operation_type TEXT NOT NULL,
                file_id INTEGER,
                user_id INTEGER NOT NULL,
                result TEXT NOT NULL,
                details TEXT,

                FOREIGN KEY (file_id)
                    REFERENCES files(id)
                    ON DELETE SET NULL,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_files_owner
                ON files(owner_id);

            CREATE INDEX IF NOT EXISTS idx_operations_user
                ON operations(user_id);

            CREATE INDEX IF NOT EXISTS idx_operations_timestamp
                ON operations(timestamp);
            """
        )


if __name__ == "__main__":
    init_database()
    print(f"База данных создана: {DATABASE_PATH}")
