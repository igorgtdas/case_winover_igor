"""
================================================================================
core/session_context.py — Contexto de Sessão do Colaborador
================================================================================

O QUE É:
    Modelo de dados que representa quem está usando o assistente em uma sessão.
    É criado uma vez (via POST /session/start) e repassado ao Orchestrator em
    cada mensagem.

PARA QUE SERVE:
    - Armazenar nome e e-mail do colaborador de suporte
    - Gerar o bloco de texto (para_texto()) injetado no system prompt dos agentes,
      personalizando respostas e habilitando auditoria de escalonamentos

O QUE USA:
    - Pydantic BaseModel → validação automática dos campos obrigatórios
    - Nenhum LLM, banco ou arquivo externo

COM QUEM CONVERSA:
    ← Criado por: api.py (endpoint POST /session/start)
    → Passado para: Orchestrator.chat() → repassado a KnowledgeAgent, DataAgent
       e EscalationAgent como session_context
    → Também usado por: core/escalation_log.py para registrar user_name/user_email

================================================================================
Contexto inicial da sessao -- variaveis capturadas antes da primeira mensagem.

Campos:
    user_name   -> nome do colaborador de suporte usando o assistente
    user_email  -> email do colaborador (auditoria e logs)
"""

from pydantic import BaseModel, Field


class SessionContext(BaseModel):
    """Variaveis de entrada coletadas no inicio da sessao."""

    user_name: str = Field(..., min_length=1)
    user_email: str = Field(...)

    def para_texto(self) -> str:
        """Bloco de texto injetado no system prompt de cada agente."""
        return (
            f"[CONTEXTO DA SESSAO]\n"
            f"Voce e o Atlas AI, assistente interno da AtlasShop.\n"
            f"Colaborador em atendimento: {self.user_name} ({self.user_email})\n"
            f"O colaborador tem acesso irrestrito a dados de todos os clientes no banco."
        )
