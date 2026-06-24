"""
Testes para tools/sql_tools.py — tools SQL para o DataAgent.
"""

from unittest.mock import patch, MagicMock


def test_get_sql_tools_returns_list(tmp_db):
    """Verifica que get_sql_tools retorna uma lista de tools."""
    with patch("core.config.DB_PATH", tmp_db), \
         patch("core.config.GROQ_API_KEY", "fake-key"), \
         patch("core.config.MODELS", {"data": "llama-3.1-8b-instant"}):
        import importlib
        import core.database
        importlib.reload(core.database)

        import tools.sql_tools as sql_module
        importlib.reload(sql_module)

        tools = sql_module.get_sql_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0


def test_get_sql_tools_contains_expected_tool_names(tmp_db):
    """Verifica que os nomes das tools SQL padrão estão presentes."""
    with patch("core.config.DB_PATH", tmp_db), \
         patch("core.config.GROQ_API_KEY", "fake-key"), \
         patch("core.config.MODELS", {"data": "llama-3.1-8b-instant"}):
        import importlib
        import core.database
        importlib.reload(core.database)

        import tools.sql_tools as sql_module
        importlib.reload(sql_module)

        tools = sql_module.get_sql_tools()
        tool_names = [t.name for t in tools]

        assert "sql_db_list_tables" in tool_names
        assert "sql_db_schema" in tool_names
        assert "sql_db_query" in tool_names
