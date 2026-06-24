"""
Testes para core/config.py — validação de carregamento de configurações.
"""

import os
from unittest.mock import patch


def test_guard_params_defaults():
    """Verifica que GUARD_PARAMS carrega com valores padrão corretos."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        # Reimporta para pegar valores padrão
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.GUARD_PARAMS["model"] == "llama-3.1-8b-instant"
        assert config_module.GUARD_PARAMS["temperature"] == 0.0
        assert config_module.GUARD_PARAMS["top_p"] == 1.0
        assert config_module.GUARD_PARAMS["max_tokens"] == 256
        assert config_module.GUARD_PARAMS["context_window"] == 0


def test_router_params_defaults():
    """Verifica que ROUTER_PARAMS carrega com valores padrão corretos."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.ROUTER_PARAMS["model"] == "llama-3.1-8b-instant"
        assert config_module.ROUTER_PARAMS["temperature"] == 0.0
        assert config_module.ROUTER_PARAMS["context_window"] == 5


def test_knowledge_params_defaults():
    """Verifica que KNOWLEDGE_PARAMS carrega com valores padrão corretos."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.KNOWLEDGE_PARAMS["model"] == "llama-3.3-70b-versatile"
        assert config_module.KNOWLEDGE_PARAMS["temperature"] == 0.1
        assert config_module.KNOWLEDGE_PARAMS["max_tokens"] == 1024
        assert config_module.KNOWLEDGE_PARAMS["context_window"] == 5


def test_data_params_defaults():
    """Verifica que DATA_PARAMS carrega com valores padrão corretos."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.DATA_PARAMS["model"] == "llama-3.3-70b-versatile"
        assert config_module.DATA_PARAMS["temperature"] == 0.0
        assert config_module.DATA_PARAMS["max_tokens"] == 1024


def test_escalation_params_defaults():
    """Verifica que ESCALATION_PARAMS carrega com valores padrão corretos."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.ESCALATION_PARAMS["model"] == "llama-3.3-70b-versatile"
        assert config_module.ESCALATION_PARAMS["temperature"] == 0.0
        assert config_module.ESCALATION_PARAMS["max_tokens"] == 512
        assert config_module.ESCALATION_PARAMS["context_window"] == 0


def test_custom_env_overrides():
    """Verifica que variáveis de ambiente customizadas sobrescrevem os padrões."""
    custom_env = {
        "GROQ_API_KEY": "custom-key",
        "GUARD_MODEL": "custom-model",
        "GUARD_TEMPERATURE": "0.5",
        "GUARD_MAX_TOKENS": "512",
        "GUARD_CONTEXT_WINDOW": "3",
    }
    with patch.dict(os.environ, custom_env, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.GUARD_PARAMS["model"] == "custom-model"
        assert config_module.GUARD_PARAMS["temperature"] == 0.5
        assert config_module.GUARD_PARAMS["max_tokens"] == 512
        assert config_module.GUARD_PARAMS["context_window"] == 3


def test_models_dict_contains_all_agents():
    """Verifica que o dicionário MODELS tem todos os agentes."""
    import importlib
    import core.config as config_module
    importlib.reload(config_module)

    expected_keys = {"guard", "router", "knowledge", "data", "escalation"}
    assert set(config_module.MODELS.keys()) == expected_keys


def test_db_path_default():
    """Verifica que DB_PATH tem valor padrão correto."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.DB_PATH == "atlasshop.db"


def test_knowledge_dir_default():
    """Verifica que KNOWLEDGE_DIR tem valor padrão correto."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
        import importlib
        import core.config as config_module
        importlib.reload(config_module)

        assert config_module.KNOWLEDGE_DIR == "knowledge"
