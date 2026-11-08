from app.database import get_connection


def log_operation(
    user_id: int,
    operation_type: str,
    result: str,
    file_id=None,
    details=None,
):
    """Запись действия пользователя в журнал аудита."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO operations (
                operation_type,
                file_id,
                user_id,
                result,
                details
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                operation_type,
                file_id,
                user_id,
                result,
                details,
            ),
        )


def get_user_operations(user_id: int):
    """Получение журнала действий конкретного пользователя."""

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                id,
                timestamp,
                operation_type,
                file_id,
                result,
                details
            FROM operations
            WHERE user_id = ?
            ORDER BY timestamp DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
