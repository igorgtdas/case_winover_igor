import logging
from pathlib import Path

from core.config import KNOWLEDGE_DIR

logger = logging.getLogger(__name__)


def load_all_docs() -> str:
    """Carrega todos os .md de knowledge/ e retorna como bloco de texto para o system prompt."""
    docs_dir = Path(KNOWLEDGE_DIR)

    if not docs_dir.is_dir():
        logger.error("Knowledge directory '%s' not found", KNOWLEDGE_DIR)
        return ""

    docs = []
    for path in sorted(docs_dir.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
            docs.append(f"### [{path.name}]\n{content}")
        except OSError as exc:
            logger.error("Failed to read knowledge file %s: %s", path, exc)

    if not docs:
        logger.warning("No .md files found in '%s'", KNOWLEDGE_DIR)

    return "\n\n---\n\n".join(docs)


def get_doc_names() -> list[str]:
    """Retorna os nomes (sem extensão) de todos os documentos disponíveis."""
    docs_dir = Path(KNOWLEDGE_DIR)
    if not docs_dir.is_dir():
        logger.error("Knowledge directory '%s' not found", KNOWLEDGE_DIR)
        return []
    return [p.stem for p in docs_dir.glob("*.md")]
