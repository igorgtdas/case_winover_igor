"""
Testes para core/knowledge_loader.py — carregamento de documentos .md.
"""

from unittest.mock import patch


def test_load_all_docs_returns_combined_text(tmp_knowledge_dir):
    """Verifica que load_all_docs retorna o texto de todos os documentos."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader as loader_module
        importlib.reload(loader_module)

        result = loader_module.load_all_docs()

        assert "FAQ Atendimento" in result
        assert "Política de Cancelamento" in result
        assert "---" in result  # separador entre documentos


def test_load_all_docs_includes_filenames(tmp_knowledge_dir):
    """Verifica que load_all_docs inclui os nomes dos arquivos como cabeçalho."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader as loader_module
        importlib.reload(loader_module)

        result = loader_module.load_all_docs()

        assert "faq_atendimento.md" in result
        assert "politica_cancelamento.md" in result


def test_load_all_docs_empty_directory(tmp_path):
    """Verifica comportamento com diretório vazio."""
    empty_dir = tmp_path / "empty_knowledge"
    empty_dir.mkdir()

    with patch("core.config.KNOWLEDGE_DIR", str(empty_dir)):
        import importlib
        import core.knowledge_loader as loader_module
        importlib.reload(loader_module)

        result = loader_module.load_all_docs()
        assert result == ""


def test_get_doc_names_returns_stems(tmp_knowledge_dir):
    """Verifica que get_doc_names retorna nomes sem extensão."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader as loader_module
        importlib.reload(loader_module)

        names = loader_module.get_doc_names()

        assert "faq_atendimento" in names
        assert "politica_cancelamento" in names
        assert len(names) == 2


def test_get_doc_names_empty_directory(tmp_path):
    """Verifica que retorna lista vazia para diretório sem .md."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with patch("core.config.KNOWLEDGE_DIR", str(empty_dir)):
        import importlib
        import core.knowledge_loader as loader_module
        importlib.reload(loader_module)

        names = loader_module.get_doc_names()
        assert names == []


def test_load_all_docs_sorted_alphabetically(tmp_knowledge_dir):
    """Verifica que os documentos são carregados em ordem alfabética."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader as loader_module
        importlib.reload(loader_module)

        result = loader_module.load_all_docs()

        # faq_atendimento deve aparecer antes de politica_cancelamento
        pos_faq = result.index("faq_atendimento")
        pos_politica = result.index("politica_cancelamento")
        assert pos_faq < pos_politica
