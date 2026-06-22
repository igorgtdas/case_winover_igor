"""
================================================================================
tools/knowledge_tools.py — Tools de Base de Conhecimento (LangChain)
================================================================================

O QUE É:
    Módulo que define duas LangChain Tools (@tool) para acesso à base de
    documentos internos da AtlasShop. Complementa core/knowledge_loader.py
    com uma interface padronizada para uso em AgentExecutors LangChain.

PARA QUE SERVE:
    - get_full_knowledge_base() → retorna todos os documentos .md concatenados
    - get_document(doc_name) → retorna um documento específico pelo nome
    Permitem que um agente LangChain com AgentExecutor decida dinamicamente
    quais documentos consultar, em vez de receber tudo no system prompt.

O QUE USA:
    - langchain_core.tools.tool → decorator que transforma função em LangChain Tool
    - core/knowledge_loader.py → load_all_docs() como backend de leitura
    - core/config.py → KNOWLEDGE_DIR para saber onde estão os arquivos
    - pathlib.Path → acesso direto ao arquivo quando doc_name é especificado

COM QUEM CONVERSA:
    ← Nenhum agente do projeto as usa diretamente no momento
       (KnowledgeAgent injeta os docs no system prompt via load_all_docs())
    → Disponíveis para extensões futuras ou uso com AgentExecutor LangChain

================================================================================
Tools disponíveis para o KnowledgeAgent.

Input/Output de cada tool:
  get_full_knowledge_base() -> str
  get_document(doc_name: str) -> str
"""

from pathlib import Path
from langchain_core.tools import tool
from core.config import KNOWLEDGE_DIR
from core.knowledge_loader import load_all_docs


@tool
def get_full_knowledge_base() -> str:
    """Retorna toda a base de conhecimento interna da AtlasShop (todos os documentos .md)."""
    return load_all_docs()


@tool
def get_document(doc_name: str) -> str:
    """
    Retorna o conteúdo de um documento específico da base de conhecimento.

    Args:
        doc_name: nome do arquivo sem extensão.
                  Exemplos: 'politica_cancelamento_reembolso_atual', 'playbook_escalonamento'
    """
    path = Path(KNOWLEDGE_DIR) / f"{doc_name}.md"
    if not path.exists():
        return f"Documento '{doc_name}' não encontrado. Documentos disponíveis: {', '.join(p.stem for p in Path(KNOWLEDGE_DIR).glob('*.md'))}"
    return path.read_text(encoding="utf-8")
