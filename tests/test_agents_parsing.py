"""
Testes para as funções de parsing dos agentes.

Testa _parse_agent_output de KnowledgeAgent e DataAgent,
e _truncar_historico usado por vários agentes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ===========================================================================
# Testes para knowledge_agent._parse_agent_output
# ===========================================================================

class TestKnowledgeAgentParser:
    """Testes para o parser de saída do KnowledgeAgent."""

    def _parse(self, raw: str):
        from agents.knowledge_agent import _parse_agent_output
        return _parse_agent_output(raw)

    def test_parse_complete_output(self):
        """Testa parsing de uma resposta completa com todos os campos."""
        raw = (
            "A política de cancelamento permite reembolso em até 7 dias.\n\n"
            "FONTES: [politica_cancelamento_reembolso_atual.md, faq_atendimento.md]\n"
            "ESCALAR: false\n"
            "MOTIVO_ESCALONAMENTO: N/A"
        )
        result = self._parse(raw)

        assert "política de cancelamento" in result.answer
        assert "politica_cancelamento_reembolso_atual.md" in result.sources
        assert "faq_atendimento.md" in result.sources
        assert result.should_escalate is False
        assert result.escalation_reason is None

    def test_parse_with_escalation(self):
        """Testa parsing quando escalonamento é necessário."""
        raw = (
            "Cliente solicita exceção comercial fora da política.\n\n"
            "FONTES: [politica_cancelamento_reembolso_atual.md]\n"
            "ESCALAR: true\n"
            "MOTIVO_ESCALONAMENTO: Cliente solicita exceção comercial não prevista"
        )
        result = self._parse(raw)

        assert result.should_escalate is True
        assert result.escalation_reason == "Cliente solicita exceção comercial não prevista"
        assert len(result.sources) == 1

    def test_parse_no_sources(self):
        """Testa parsing quando não há marcação de fontes."""
        raw = "Resposta simples sem marcações estruturadas."
        result = self._parse(raw)

        assert result.sources == []
        assert result.should_escalate is False
        assert result.escalation_reason is None

    def test_parse_escalar_true_case_insensitive(self):
        """Testa que o parser aceita ESCALAR: True (case insensitive)."""
        raw = "Resposta.\nFONTES: [doc.md]\nESCALAR: True\nMOTIVO_ESCALONAMENTO: Urgente"
        result = self._parse(raw)

        assert result.should_escalate is True

    def test_parse_motivo_na_ignored(self):
        """Testa que MOTIVO_ESCALONAMENTO: N/A resulta em None."""
        raw = "Resposta.\nFONTES: [doc.md]\nESCALAR: false\nMOTIVO_ESCALONAMENTO: N/A"
        result = self._parse(raw)

        assert result.escalation_reason is None

    def test_parse_motivo_none_ignored(self):
        """Testa que MOTIVO_ESCALONAMENTO: None resulta em None."""
        raw = "Resposta.\nFONTES: [doc.md]\nESCALAR: false\nMOTIVO_ESCALONAMENTO: None"
        result = self._parse(raw)

        assert result.escalation_reason is None

    def test_parse_multiple_sources(self):
        """Testa parsing com múltiplas fontes."""
        raw = "Resposta.\nFONTES: [doc1.md, doc2.md, doc3.md]\nESCALAR: false\nMOTIVO_ESCALONAMENTO: N/A"
        result = self._parse(raw)

        assert len(result.sources) == 3
        assert "doc1.md" in result.sources
        assert "doc2.md" in result.sources
        assert "doc3.md" in result.sources

    def test_parse_answer_contains_full_raw(self):
        """Verifica que o campo answer contém o texto completo."""
        raw = "Texto completo com\nmúltiplas linhas.\nFONTES: [x.md]\nESCALAR: false\nMOTIVO_ESCALONAMENTO: N/A"
        result = self._parse(raw)

        assert result.answer == raw


# ===========================================================================
# Testes para data_agent._parse_agent_output
# ===========================================================================

class TestDataAgentParser:
    """Testes para o parser de saída do DataAgent."""

    def _parse(self, raw: str):
        from agents.data_agent import _parse_agent_output
        return _parse_agent_output(raw)

    def test_parse_complete_output(self):
        """Testa parsing de uma resposta completa do DataAgent."""
        raw = (
            "O pedido P1001 está ativo com pagamento confirmado.\n\n"
            "ESCALAR: false\n"
            "NIVEL: none\n"
            "MOTIVO: N/A\n"
            "SQL_USADO: SELECT * FROM pedidos WHERE pedido_id = 'P1001'"
        )
        result = self._parse(raw)

        assert result.should_escalate is False
        assert result.sql_used == "SELECT * FROM pedidos WHERE pedido_id = 'P1001'"
        assert result.escalation_reason is None

    def test_parse_with_fraud_escalation(self):
        """Testa parsing quando há escalonamento por fraude."""
        raw = (
            "O pedido P1008 está em fraud_review.\n\n"
            "ESCALAR: true\n"
            "NIVEL: Risco\n"
            "MOTIVO: Pedido em fraud_review sem resolução há 30 dias\n"
            "SQL_USADO: SELECT * FROM pedidos WHERE status_pagamento = 'fraud_review'"
        )
        result = self._parse(raw)

        assert result.should_escalate is True
        assert "[Risco]" in result.escalation_reason
        assert "fraud_review" in result.escalation_reason

    def test_parse_with_financial_escalation(self):
        """Testa parsing com escalonamento Financeiro."""
        raw = (
            "Chargeback detectado.\n\n"
            "ESCALAR: true\n"
            "NIVEL: Financeiro\n"
            "MOTIVO: Chargeback aberto na operadora\n"
            "SQL_USADO: SELECT * FROM pedidos WHERE status_pagamento = 'chargeback'"
        )
        result = self._parse(raw)

        assert result.should_escalate is True
        assert "[Financeiro]" in result.escalation_reason

    def test_parse_no_sql(self):
        """Testa parsing quando não há SQL usado."""
        raw = "Resposta sem SQL.\nESCALAR: false\nNIVEL: none\nMOTIVO: N/A\nSQL_USADO: N/A"
        result = self._parse(raw)

        assert result.sql_used is None

    def test_parse_no_structured_output(self):
        """Testa parsing quando o LLM não incluiu marcações."""
        raw = "Resposta livre sem nenhuma marcação estruturada."
        result = self._parse(raw)

        assert result.should_escalate is False
        assert result.sql_used is None
        assert result.escalation_reason is None
        assert result.answer == raw

    def test_parse_nivel_l2(self):
        """Testa parsing com nível L2."""
        raw = "Conflito de regras.\nESCALAR: true\nNIVEL: L2\nMOTIVO: Conflito entre políticas\nSQL_USADO: N/A"
        result = self._parse(raw)

        assert result.should_escalate is True
        assert "[L2]" in result.escalation_reason

    def test_parse_answer_contains_full_raw(self):
        """Verifica que o campo answer contém o texto completo."""
        raw = "Texto completo.\nESCALAR: false\nNIVEL: none\nMOTIVO: N/A\nSQL_USADO: N/A"
        result = self._parse(raw)

        assert result.answer == raw


# ===========================================================================
# Testes para _truncar_historico (usado por router, knowledge, data agents)
# ===========================================================================

class TestTruncarHistorico:
    """Testes para a função _truncar_historico."""

    def _truncar(self, chat_history, context_window):
        from agents.router_agent import _truncar_historico
        return _truncar_historico(chat_history, context_window)

    def test_context_window_zero_returns_empty(self):
        """context_window=0 deve retornar lista vazia."""
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
        ]
        result = self._truncar(history, 0)
        assert result == []

    def test_context_window_one_returns_last_turn(self):
        """context_window=1 deve retornar o último turno (2 mensagens)."""
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": "resp2"},
        ]
        result = self._truncar(history, 1)
        assert len(result) == 2
        assert result[0]["content"] == "msg2"
        assert result[1]["content"] == "resp2"

    def test_context_window_larger_than_history(self):
        """context_window maior que o histórico retorna tudo."""
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
        ]
        result = self._truncar(history, 10)
        assert len(result) == 2

    def test_empty_history(self):
        """Histórico vazio retorna lista vazia."""
        result = self._truncar([], 5)
        assert result == []

    def test_context_window_two_returns_last_two_turns(self):
        """context_window=2 deve retornar os últimos 2 turnos (4 mensagens)."""
        history = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": "resp2"},
            {"role": "user", "content": "msg3"},
            {"role": "assistant", "content": "resp3"},
        ]
        result = self._truncar(history, 2)
        assert len(result) == 4
        assert result[0]["content"] == "msg2"


# ===========================================================================
# Testes para GuardOutput model
# ===========================================================================

class TestGuardOutput:
    """Testes para o modelo GuardOutput."""

    def test_guard_output_allow(self):
        from agents.guard_agent import GuardOutput
        output = GuardOutput(action="allow", category="clean", reason="mensagem legítima")
        assert output.action == "allow"
        assert output.category == "clean"

    def test_guard_output_block(self):
        from agents.guard_agent import GuardOutput
        output = GuardOutput(action="block", category="security", reason="prompt injection")
        assert output.action == "block"
        assert output.category == "security"

    def test_guard_output_warn(self):
        from agents.guard_agent import GuardOutput
        output = GuardOutput(action="warn", category="safety", reason="conteúdo ambíguo")
        assert output.action == "warn"
        assert output.category == "safety"


# ===========================================================================
# Testes para RouterOutput model
# ===========================================================================

class TestRouterOutput:
    """Testes para o modelo RouterOutput."""

    def test_router_output_knowledge(self):
        from agents.router_agent import RouterOutput
        output = RouterOutput(agent="knowledge", reasoning="pergunta sobre política")
        assert output.agent == "knowledge"

    def test_router_output_data(self):
        from agents.router_agent import RouterOutput
        output = RouterOutput(agent="data", reasoning="consulta de pedido")
        assert output.agent == "data"

    def test_router_output_escalation(self):
        from agents.router_agent import RouterOutput
        output = RouterOutput(agent="escalation", reasoning="ameaça judicial")
        assert output.agent == "escalation"


# ===========================================================================
# Testes para EscalationOutput model
# ===========================================================================

class TestEscalationOutput:
    """Testes para o modelo EscalationOutput."""

    def test_escalation_output_no_escalation(self):
        from agents.escalation_agent import EscalationOutput
        output = EscalationOutput(
            should_escalate=False,
            level="none",
            reason="Situação resolvida",
            evidence="N/A",
            next_steps="N/A",
        )
        assert output.should_escalate is False
        assert output.level == "none"

    def test_escalation_output_risco(self):
        from agents.escalation_agent import EscalationOutput
        output = EscalationOutput(
            should_escalate=True,
            level="Risco",
            reason="Fraude confirmada",
            evidence="Pedido P1008 em fraud_review",
            next_steps="Encaminhar para time de Risco",
        )
        assert output.should_escalate is True
        assert output.level == "Risco"

    def test_escalation_output_financeiro(self):
        from agents.escalation_agent import EscalationOutput
        output = EscalationOutput(
            should_escalate=True,
            level="Financeiro",
            reason="Chargeback",
            evidence="Chargeback aberto",
            next_steps="Encaminhar para Financeiro",
        )
        assert output.level == "Financeiro"
