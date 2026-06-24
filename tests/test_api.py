"""
Testes para api.py — endpoints REST do AtlasShop Assist.
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Cria um TestClient para a API com Orchestrator mockado."""
    # Mock the Orchestrator at the module level before it's used
    mock_orchestrator_class = MagicMock()
    mock_instance = MagicMock()
    mock_instance.chat.return_value = "Resposta de teste do assistente."
    mock_instance.chat_history = [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Resposta de teste do assistente."},
    ]
    mock_orchestrator_class.return_value = mock_instance

    with patch.dict("sys.modules", {}):
        pass

    with patch("orchestrator.GuardAgent"), \
         patch("orchestrator.RouterAgent"), \
         patch("orchestrator.KnowledgeAgent"), \
         patch("orchestrator.DataAgent"), \
         patch("orchestrator.EscalationAgent"):

        import importlib
        import api as api_module
        importlib.reload(api_module)

        # Clear sessions and patch the Orchestrator reference in api module
        api_module._sessions.clear()
        api_module.Orchestrator = mock_orchestrator_class

        yield TestClient(api_module.app)


@pytest.fixture
def client_with_error():
    """Cria um TestClient onde o Orchestrator lança exceção."""
    mock_orchestrator_class = MagicMock()
    mock_instance = MagicMock()
    mock_instance.chat.side_effect = RuntimeError("Erro de API Groq")
    mock_instance.chat_history = []
    mock_orchestrator_class.return_value = mock_instance

    with patch("orchestrator.GuardAgent"), \
         patch("orchestrator.RouterAgent"), \
         patch("orchestrator.KnowledgeAgent"), \
         patch("orchestrator.DataAgent"), \
         patch("orchestrator.EscalationAgent"):

        import importlib
        import api as api_module
        importlib.reload(api_module)

        api_module._sessions.clear()
        api_module.Orchestrator = mock_orchestrator_class

        yield TestClient(api_module.app)


class TestHealthEndpoint:
    """Testes para GET /health."""

    def test_health_returns_ok(self, client):
        """Verifica que /health retorna status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "sessions_ativas" in data

    def test_health_shows_zero_sessions_initially(self, client):
        """Verifica que inicia com 0 sessões ativas."""
        response = client.get("/health")
        assert response.json()["sessions_ativas"] == 0


class TestChatEndpoint:
    """Testes para POST /chat."""

    def test_chat_basic_request(self, client):
        """Envia uma mensagem básica e recebe resposta."""
        response = client.post("/chat", json={
            "message": "Qual a política de reembolso?",
            "session_id": "test-session",
            "user_id": "user-1",
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["session_id"] == "test-session"

    def test_chat_creates_session(self, client):
        """Verifica que uma sessão é criada na primeira mensagem."""
        response = client.post("/chat", json={
            "message": "Olá",
            "session_id": "new-session",
        })
        assert response.status_code == 200
        assert response.json()["session_id"] == "new-session"

    def test_chat_default_session_id(self, client):
        """Verifica que session_id padrão é 'default'."""
        response = client.post("/chat", json={
            "message": "Teste",
        })
        assert response.status_code == 200
        assert response.json()["session_id"] == "default"

    def test_chat_empty_message_rejected(self, client):
        """Mensagem vazia deve ser rejeitada pela validação."""
        response = client.post("/chat", json={
            "message": "",
            "session_id": "test",
        })
        assert response.status_code == 422  # Validation error

    def test_chat_message_too_long_rejected(self, client):
        """Mensagem acima de 4000 caracteres deve ser rejeitada."""
        response = client.post("/chat", json={
            "message": "x" * 4001,
            "session_id": "test",
        })
        assert response.status_code == 422

    def test_chat_orchestrator_exception(self, client_with_error):
        """Quando o Orchestrator lança exceção, retorna 500."""
        response = client_with_error.post("/chat", json={
            "message": "Teste",
            "session_id": "error-session",
        })
        assert response.status_code == 500
        assert "Erro ao processar" in response.json()["detail"]


class TestHistoryEndpoint:
    """Testes para GET /session/{session_id}/history."""

    def test_history_session_not_found(self, client):
        """Sessão inexistente retorna 404."""
        response = client.get("/session/inexistente/history")
        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"]

    def test_history_returns_messages(self, client):
        """Após enviar mensagem, histórico deve retornar as mensagens."""
        # Primeira: cria a sessão
        client.post("/chat", json={
            "message": "Olá",
            "session_id": "hist-session",
        })
        # Busca histórico
        response = client.get("/session/hist-session/history")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "hist-session"
        assert "messages" in data
        assert "total" in data


class TestClearSessionEndpoint:
    """Testes para DELETE /session/{session_id}."""

    def test_clear_existing_session(self, client):
        """Encerrar sessão existente retorna sucesso."""
        # Cria sessão
        client.post("/chat", json={
            "message": "Olá",
            "session_id": "to-clear",
        })
        # Encerra
        response = client.delete("/session/to-clear")
        assert response.status_code == 200
        assert "encerrada" in response.json()["message"]

    def test_clear_nonexistent_session_idempotent(self, client):
        """Encerrar sessão inexistente é idempotente (retorna 200)."""
        response = client.delete("/session/nao-existe")
        assert response.status_code == 200

    def test_clear_session_removes_from_memory(self, client):
        """Após encerrar, sessão não deve estar mais acessível."""
        # Cria sessão
        client.post("/chat", json={
            "message": "Olá",
            "session_id": "temp-session",
        })
        # Encerra
        client.delete("/session/temp-session")
        # Verifica que não existe mais
        response = client.get("/session/temp-session/history")
        assert response.status_code == 404


class TestChatRequestValidation:
    """Testes de validação do schema ChatRequest."""

    def test_missing_message_field(self, client):
        """Requisição sem campo 'message' deve falhar."""
        response = client.post("/chat", json={
            "session_id": "test",
        })
        assert response.status_code == 422

    def test_invalid_json_body(self, client):
        """Body inválido deve retornar erro."""
        response = client.post("/chat", content="not json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422
