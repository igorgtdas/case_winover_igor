"""
================================================================================
core/knowledge_loader.py — Carregador de Base de Conhecimento
================================================================================

O QUE É:
    Utilitário que lê todos os arquivos .md da pasta knowledge/ e os concatena
    em um único bloco de texto pronto para ser injetado no system prompt dos agentes.

PARA QUE SERVE:
    - load_all_docs() → retorna toda a base de conhecimento como string formatada,
      com separadores entre documentos e cabeçalho com nome do arquivo
    - get_doc_names() → lista os nomes dos documentos disponíveis (sem extensão)

    Os documentos são a única fonte de verdade dos agentes KnowledgeAgent e
    EscalationAgent — eles nunca inventam informações além do que está nos .md.

O QUE USA:
    - pathlib.Path → leitura de arquivos .md do sistema de arquivos
    - core/config.py → lê KNOWLEDGE_DIR (.env ou padrão "knowledge/")
    - Nenhum LLM ou banco de dados

COM QUEM CONVERSA:
    ← Nenhum (módulo folha)
    → Usado por: agents/knowledge_agent.py, agents/data_agent.py (knowledge_summary),
       agents/escalation_agent.py (playbook), tools/knowledge_tools.py
"""

from pathlib import Path
from core.config import KNOWLEDGE_DIR


def load_all_docs() -> str:
    """Carrega todos os .md de knowledge/ e retorna como bloco de texto para o system prompt."""
    docs_dir = Path(KNOWLEDGE_DIR)
    docs = []

    for path in sorted(docs_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        docs.append(f"### [{path.name}]\n{content}")

    return "\n\n---\n\n".join(docs)


def get_doc_names() -> list[str]:
    """Retorna os nomes (sem extensão) de todos os documentos disponíveis."""
    return [p.stem for p in Path(KNOWLEDGE_DIR).glob("*.md")]
