"""
================================================================================
core/database.py — Conexão com o Banco de Dados SQLite
================================================================================

O QUE É:
    Módulo de infraestrutura de banco de dados. Centraliza a criação de conexões
    com o arquivo SQLite (atlasshop.db) para que nenhum agente precise saber o
    caminho ou o driver usado.

PARA QUE SERVE:
    - get_engine() → retorna um SQLAlchemy Engine para execução de queries brutas
      (usado pelo DataAgent para executar SELECT gerado pelo LLM)
    - get_langchain_db() → retorna um SQLDatabase do LangChain para integração
      com toolkits (usado por tools/sql_tools.py)

O QUE USA:
    - SQLAlchemy (create_engine) → driver SQLite nativo do Python
    - langchain_community.utilities.SQLDatabase → wrapper LangChain sobre SQLAlchemy
    - core/config.py → lê DB_PATH (.env ou padrão "atlasshop.db")

COM QUEM CONVERSA:
    ← Nenhum (módulo folha)
    → Usado por: agents/data_agent.py (get_engine) e tools/sql_tools.py
       (get_langchain_db), core/escalation_log.py (get_engine)
"""

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from core.config import DB_PATH


def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def get_langchain_db() -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
