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
