"""
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
