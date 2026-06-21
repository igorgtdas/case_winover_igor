"""
Fábrica centralizada para instâncias do LLM (ChatGroq).

Evita repetição do padrão de inicialização do ChatGroq em cada agente.
"""

from langchain_groq import ChatGroq
from core.config import GROQ_API_KEY


def create_llm(params: dict) -> ChatGroq:
    """
    Cria uma instância do ChatGroq a partir do dicionário de parâmetros de um agente.

    Args:
        params: dicionário com chaves 'model', 'temperature', 'max_tokens'
                (formato usado em core.config: GUARD_PARAMS, ROUTER_PARAMS, etc.)
    """
    return ChatGroq(
        model=params["model"],
        api_key=GROQ_API_KEY,
        temperature=params["temperature"],
        max_tokens=params["max_tokens"],
    )
