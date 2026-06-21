import logging
from pathlib import Path

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from core.config import DB_PATH

logger = logging.getLogger(__name__)


def get_engine():
    if not Path(DB_PATH).is_file():
        raise FileNotFoundError(
            f"Database file '{DB_PATH}' not found. Run 'python setup_db.py' first."
        )
    return create_engine(f"sqlite:///{DB_PATH}")


def get_langchain_db() -> SQLDatabase:
    if not Path(DB_PATH).is_file():
        raise FileNotFoundError(
            f"Database file '{DB_PATH}' not found. Run 'python setup_db.py' first."
        )
    return SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
