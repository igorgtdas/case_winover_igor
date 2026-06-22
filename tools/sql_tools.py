"""
================================================================================
tools/sql_tools.py — Tools SQL via LangChain SQLDatabaseToolkit
================================================================================

O QUE É:
    Módulo que instancia o SQLDatabaseToolkit do LangChain e expõe as 4 tools
    SQL automáticas para uso com AgentExecutors LangChain.

PARA QUE SERVE:
    Fornecer tools SQL padronizadas para agentes que precisam explorar o banco
    de forma dinâmica (schema discovery + execução de queries):
      - sql_db_list_tables   → lista as tabelas disponíveis
      - sql_db_schema        → retorna DDL + exemplos de uma tabela
      - sql_db_query         → executa SELECT e retorna resultado
      - sql_db_query_checker → valida a query antes de executar

O QUE USA:
    - langchain_community.agent_toolkits.SQLDatabaseToolkit → gera as 4 tools
    - langchain_groq.ChatGroq → LLM exigido pelo toolkit para query_checker
    - core/database.py → get_langchain_db() para conectar ao SQLite
    - core/config.py → MODELS["data"] e GROQ_API_KEY

COM QUEM CONVERSA:
    ← Nenhum agente do projeto as usa diretamente no momento
       (DataAgent usa SQLAlchemy direto + LLM em duas chains separadas)
    → Disponíveis para extensões futuras ou uso com AgentExecutor LangChain

================================================================================
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

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from core.database import get_langchain_db
from core.config import MODELS, GROQ_API_KEY


def get_sql_tools() -> list:
    """Retorna as tools SQL vinculadas ao banco SQLite da AtlasShop."""
    db = get_langchain_db()
    llm = ChatGroq(model=MODELS["data"], api_key=GROQ_API_KEY, temperature=0)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()
