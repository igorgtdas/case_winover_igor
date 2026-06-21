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

Segurança:
  - A tool sql_db_query é substituída por uma versão que rejeita
    qualquer query que não seja SELECT (previne INSERT/UPDATE/DELETE/DROP).
"""

import re

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from core.database import get_langchain_db
from core.config import MODELS, GROQ_API_KEY

_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|MERGE|EXEC|EXECUTE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def get_sql_tools() -> list:
    """Retorna as tools SQL vinculadas ao banco SQLite da AtlasShop."""
    db = get_langchain_db()
    llm = ChatGroq(model=MODELS["data"], api_key=GROQ_API_KEY, temperature=0)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    raw_tools = toolkit.get_tools()

    safe_tools = []
    for t in raw_tools:
        if t.name == "sql_db_query":
            original_run = t._run

            def _safe_run(query: str, _orig=original_run) -> str:
                if _FORBIDDEN_PATTERN.search(query):
                    return "Erro: apenas queries SELECT são permitidas."
                return _orig(query)

            t._run = _safe_run
        safe_tools.append(t)

    return safe_tools
