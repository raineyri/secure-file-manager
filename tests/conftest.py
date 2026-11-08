import pytest

import app.config as config
import app.database as database
import app.file_service as file_service
import app.archive_service as archive_service


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """
    Каждый тест получает отдельную временную
    директорию и отдельную SQLite-базу.
    """

    storage_dir = tmp_path / "storage"
    data_dir = tmp_path / "data"
    database_path = data_dir / "test.db"

    storage_dir.mkdir()
    data_dir.mkdir()

    monkeypatch.setattr(
        config,
        "STORAGE_DIR",
        storage_dir,
    )

    monkeypatch.setattr(
        config,
        "DATA_DIR",
        data_dir,
    )

    monkeypatch.setattr(
        config,
        "DATABASE_PATH",
        database_path,
    )

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        database_path,
    )

    monkeypatch.setattr(
        file_service,
        "STORAGE_DIR",
        storage_dir,
    )

    monkeypatch.setattr(
        archive_service,
        "STORAGE_DIR",
        storage_dir,
    )

    database.init_database()

    yield
