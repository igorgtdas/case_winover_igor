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
    safe_name = Path(doc_name).name
    if safe_name != doc_name:
        return f"Nome de documento inválido: '{doc_name}'"
    path = (Path(KNOWLEDGE_DIR) / f"{safe_name}.md").resolve()
    knowledge_root = Path(KNOWLEDGE_DIR).resolve()
    if not str(path).startswith(str(knowledge_root)):
        return f"Nome de documento inválido: '{doc_name}'"
    if not path.exists():
        return f"Documento '{doc_name}' não encontrado. Documentos disponíveis: {', '.join(p.stem for p in Path(KNOWLEDGE_DIR).glob('*.md'))}"
    return path.read_text(encoding="utf-8")
