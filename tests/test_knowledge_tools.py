"""
Testes para tools/knowledge_tools.py — tools de consulta de documentos.
"""

from pathlib import Path
from unittest.mock import patch


def test_get_full_knowledge_base_returns_all_docs(tmp_knowledge_dir):
    """Verifica que get_full_knowledge_base retorna todos os documentos."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader
        importlib.reload(core.knowledge_loader)

        # Reimporta tools para pegar o loader atualizado
        import tools.knowledge_tools as kt_module
        importlib.reload(kt_module)

        result = kt_module.get_full_knowledge_base.invoke("")
        assert "FAQ Atendimento" in result
        assert "Política de Cancelamento" in result


def test_get_document_returns_specific_doc(tmp_knowledge_dir):
    """Verifica que get_document retorna o conteúdo de um doc específico."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader
        importlib.reload(core.knowledge_loader)

        import tools.knowledge_tools as kt_module
        importlib.reload(kt_module)

        result = kt_module.get_document.invoke("faq_atendimento")
        assert "FAQ Atendimento" in result
        assert "Horário de atendimento" in result


def test_get_document_not_found(tmp_knowledge_dir):
    """Verifica mensagem de erro quando documento não existe."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader
        importlib.reload(core.knowledge_loader)

        import tools.knowledge_tools as kt_module
        importlib.reload(kt_module)

        result = kt_module.get_document.invoke("documento_inexistente")
        assert "não encontrado" in result
        assert "faq_atendimento" in result  # deve listar docs disponíveis


def test_get_document_lists_available_docs_on_error(tmp_knowledge_dir):
    """Verifica que a mensagem de erro lista os documentos disponíveis."""
    with patch("core.config.KNOWLEDGE_DIR", tmp_knowledge_dir):
        import importlib
        import core.knowledge_loader
        importlib.reload(core.knowledge_loader)

        import tools.knowledge_tools as kt_module
        importlib.reload(kt_module)

        result = kt_module.get_document.invoke("xyz_missing")
        assert "politica_cancelamento" in result
        assert "faq_atendimento" in result
