from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"

DATABASE_PATH = DATA_DIR / "file_manager.db"


def init_directories():
    """Создание служебных каталогов приложения."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
