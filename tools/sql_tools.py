"""
Tools SQL disponíveis para o DataAgent.

O LangChain SQLDatabaseToolkit expõe 4 tools automaticamente:
  - sql_db_list_tables   → lista as tabelas disponíveis
  - sql_db_schema        → retorna schema + 3 linhas de exemplo de uma tabela
  - sql_db_query         → executa uma query SELECT e retorna resultado
  - sql_db_query_checker → valida uma query SQL antes de executar

Input/Output (gerado pelo toolkit):
  sql_db_list_tables(tool_input: "") -> "clientes, pedidos, reembolsos"
  sql_db_schema(table_names: str)    -> "<CREATE TABLE ...>"
  sql_db_query(query: str)           -> "<resultado em texto>"
  sql_db_query_checker(query: str)   -> "<query corrigida ou erro>"
"""

import logging

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from core.database import get_langchain_db
from core.config import MODELS, GROQ_API_KEY

logger = logging.getLogger(__name__)


def get_sql_tools() -> list:
    """Retorna as tools SQL vinculadas ao banco SQLite da AtlasShop."""
    try:
        db = get_langchain_db()
    except FileNotFoundError:
        logger.error(
            "Database not found. SQL tools will be unavailable. "
            "Run 'python setup_db.py' to create it."
        )
        raise

    llm = ChatGroq(model=MODELS["data"], api_key=GROQ_API_KEY, temperature=0)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()
