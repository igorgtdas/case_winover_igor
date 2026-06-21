"""
Testes para core/database.py — conexão com o banco SQLite.
"""

from unittest.mock import patch
from sqlalchemy import Engine


def test_get_engine_returns_engine(tmp_db):
    """Verifica que get_engine retorna um SQLAlchemy Engine válido."""
    with patch("core.config.DB_PATH", tmp_db):
        # Reimporta com o path mockado
        import importlib
        import core.database as db_module
        importlib.reload(db_module)

        engine = db_module.get_engine()
        assert isinstance(engine, Engine)
        assert "sqlite" in str(engine.url)


def test_get_langchain_db_returns_sqldatabase(tmp_db):
    """Verifica que get_langchain_db retorna um objeto SQLDatabase funcional."""
    with patch("core.config.DB_PATH", tmp_db):
        import importlib
        import core.database as db_module
        importlib.reload(db_module)

        db = db_module.get_langchain_db()
        # SQLDatabase deve ter método get_usable_table_names
        tables = db.get_usable_table_names()
        assert "clientes" in tables
        assert "pedidos" in tables
        assert "reembolsos" in tables


def test_get_engine_connects_to_correct_path(tmp_db):
    """Verifica que o engine conecta no caminho correto do DB."""
    with patch("core.config.DB_PATH", tmp_db):
        import importlib
        import core.database as db_module
        importlib.reload(db_module)

        engine = db_module.get_engine()
        assert tmp_db in str(engine.url)
