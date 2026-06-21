from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from core.config import DB_PATH


def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def get_langchain_db() -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
