"""
================================================================================
orchestrator.py — Controlador Principal do Fluxo Conversacional
================================================================================

O QUE É:
    Cérebro do sistema. A classe Orchestrator coordena todos os agentes em
    sequência para cada mensagem recebida, mantém o histórico da sessão e decide
    o que o usuário vê (e o que fica só no log interno).

PARA QUE SERVE:
    Executar o pipeline completo para cada mensagem:
      1. GuardAgent → filtra segurança e safety
           - block security   → registra no escalation_log como nível Risco
           - block safety     → bloqueia sem registrar
           - should_escalate  → STOP CHECKER: bypassa o Router, vai direto ao Escalation
      2. RouterAgent → classifica intenção (knowledge | data | escalation)
      3. Agente alvo → KnowledgeAgent, DataAgent ou EscalationAgent
      4. Se escalation: persiste relatório no banco, usuário recebe mensagem padrão
      5. Gerencia estado de "reclamação pendente" (quando pedido_id não foi informado)
      6. Atualiza o chat_history (user → tool traces → assistant)

O QUE USA:
    - agents/guard_agent.py, router_agent.py, knowledge_agent.py,
      data_agent.py, escalation_agent.py → todos os agentes do sistema
    - core/session_context.py → contexto do colaborador (nome, e-mail)
    - tools/escalation_tool.py → persiste escalonamentos no SQLite
    - core/rate_limit.py → captura RateLimitError do Groq e retorna mensagem amigável

COM QUEM CONVERSA:
    ← Chamado por: api.py (endpoint POST /chat) a cada mensagem
    → Chama: todos os agentes em sequência conforme o fluxo acima
    → Persiste em: core/escalation_log.py (banco SQLite)

================================================================================
Orchestrator — Controlador principal do fluxo conversacional

Fluxo por mensagem:
  1. GuardAgent      → checa segurança e safety
       → block security: registra no log de escalamento (nível Risco) e rejeita
       → block safety: rejeita sem registrar (fora de escopo / impróprio)
       → block (sem should_escalate): retorna mensagem de rejeição, para aqui
       → should_escalate=True: STOP CHECKER — vai direto ao EscalationAgent, ignora Router
       → allow/warn: segue o fluxo normal
  2. RouterAgent     → classifica intenção → knowledge | data | escalation
  3. Agente alvo     → KnowledgeAgent | DataAgent | EscalationAgent direto
  4. Se router_result.agent == "escalation":
       - EscalationAgent gera relatório estruturado
       - Relatório é salvo em escalation_logs no banco
       - Usuário recebe mensagem padrão (não vê os detalhes internos)
  5. Atualiza histórico e retorna resposta
"""

import logging
from agents.guard_agent      import GuardAgent,      GuardInput
from agents.router_agent     import RouterAgent,     RouterInput
from agents.knowledge_agent  import KnowledgeAgent,  KnowledgeInput
from agents.data_agent       import DataAgent,       DataInput
from agents.escalation_agent import EscalationAgent, EscalationInput
from core.session_context    import SessionContext
from tools.escalation_tool   import log_escalation as registrar_escalamento
from core.rate_limit         import RateLimitError, MENSAGEM_RATE_LIMIT

# Mensagem exibida ao usuário quando há escalonamento
# Não revela detalhes internos — apenas orienta o redirecionamento
_MENSAGEM_ESCALONAMENTO = (
    "Infelizmente não consigo atender a essa solicitação pelo assistente. "
    "Sua situação foi registrada e será encaminhada para o time responsável. "
    "Por favor, aguarde o contato ou abra um chamado diretamente com o suporte."
)


logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.guard      = GuardAgent()
        self.router     = RouterAgent()
        self.knowledge  = KnowledgeAgent()
        self.data       = DataAgent()
        self.escalation = EscalationAgent()
        self.chat_history: list[dict] = []
        self.system_prompt_preview: str | None = None
        # Estado de reclamação pendente: aguardando pedido_id do colaborador
        self._pending_reclamacao: dict | None = None

    def chat(
        self,
        user_message: str,
        user_id: str = "user",
        session_id: str = "default",
        session_context: SessionContext | None = None,
    ) -> str:
        user_name   = session_context.user_name  if session_context else None
        user_email  = session_context.user_email if session_context else None

        if session_context and self.system_prompt_preview is None:
            self.system_prompt_preview = session_context.para_texto()

        # 1. Guard
        guard_result = self.guard.run(GuardInput(
            content=user_message,
            user_id=user_id,
            session_id=session_id,
        ))

        logger.info("Guard result: action=%s category=%s should_escalate=%s reason=%s",
                    guard_result.action, guard_result.category,
                    guard_result.should_escalate, guard_result.reason)

        if guard_result.action == "block" and not guard_result.should_escalate:
            blocked_msg = (
                "Infelizmente não consigo processar essa mensagem. "
                "Por favor, mantenha o foco no suporte AtlasShop."
            )
            # Tentativas de security (injection, jailbreak, bypass) são registradas
            # Safety (fora de escopo, conteúdo impróprio) apenas bloqueia, sem log
            if guard_result.category == "security":
                registrar_escalamento(
                    session_id=session_id,
                    user_id=user_id,
                    mensagem_usuario=user_message,
                    nivel="Risco",
                    motivo=guard_result.reason,
                    evidencia=user_message,
                    proximos_passos="Revisar tentativa de bypass/injection no log de segurança.",
                    triggered_by="guard_agent",
                    user_name=user_name,
                    user_email=user_email,
                )
            self.chat_history.append({"role": "user",      "content": user_message, "agent_selected": "guard"})
            self.chat_history.append({"role": "assistant",  "content": blocked_msg,  "agent_selected": "guard"})
            return blocked_msg, "guard"

        # Stop checker determinístico: Guard detectou situação grave → bypass Router
        if guard_result.should_escalate:
            esc = self.escalation.run(EscalationInput(
                situation=user_message,
                evidence=guard_result.reason,
                triggered_by="guard_agent",
                client_plan=None,
            ))
            registrar_escalamento(
                session_id=session_id,
                user_id=user_id,
                mensagem_usuario=user_message,
                nivel=esc.level,
                motivo=esc.reason,
                evidencia=esc.evidence,
                proximos_passos=esc.next_steps,
                triggered_by="guard_agent",
                user_name=user_name,
                user_email=user_email,
                plano=None,
            )
            self.chat_history.append({"role": "user",      "content": user_message,           "agent_selected": "guard_escalation"})
            self.chat_history.append({"role": "assistant",  "content": _MENSAGEM_ESCALONAMENTO, "agent_selected": "guard_escalation"})
            return _MENSAGEM_ESCALONAMENTO, "guard_escalation"

        # Reclamação pendente: colaborador respondeu com o pedido_id
        if self._pending_reclamacao is not None:
            import re
            match = re.search(r'\b(P\d+)\b', user_message, re.IGNORECASE)
            pedido_id_resposta = match.group(1).upper() if match else user_message.strip()

            pending = self._pending_reclamacao
            self._pending_reclamacao = None

            esc = self.escalation.run(EscalationInput(
                situation=pending["situation"],
                evidence=pending["evidence"],
                triggered_by=pending["triggered_by"],
                client_plan=None,
                tipo="reclamacao",
                pedido_id=pedido_id_resposta,
                colaborador_nome=user_name,
                colaborador_email=user_email,
            ))

            registrar_escalamento(
                session_id=session_id,
                user_id=user_id,
                mensagem_usuario=pending["mensagem_original"],
                nivel=esc.level,
                motivo=esc.reason,
                evidencia=esc.evidence,
                proximos_passos=esc.next_steps,
                triggered_by=pending["triggered_by"],
                user_name=user_name,
                user_email=user_email,
                plano=None,
                pedido_id=pedido_id_resposta,
                tipo="reclamacao",
            )

            confirmacao = (
                f"Reclamação registrada com sucesso para o pedido {pedido_id_resposta}. "
                f"O time responsável será acionado. "
                f"Número de protocolo: ESC-{session_id[-6:].upper()}."
            )
            self.chat_history.append({"role": "user",      "content": user_message,  "agent_selected": "escalation"})
            self.chat_history.append({"role": "assistant",  "content": confirmacao,   "agent_selected": "escalation"})
            return confirmacao, "escalation"

        try:
            # 2. Router
            router_result = self.router.run(RouterInput(
                content=user_message,
                chat_history=self.chat_history,
            ))

            # 3. Agente alvo
            response_text = ""
            tool_traces: list = []

            if router_result.agent == "knowledge":
                result = self.knowledge.run(KnowledgeInput(
                    question=user_message,
                    chat_history=self.chat_history,
                    session_context=session_context,
                ))
                response_text = result.answer
                tool_traces = [t.to_history_entry() for t in result.traces]

            elif router_result.agent == "data":
                result = self.data.run(DataInput(
                    question=user_message,
                    chat_history=self.chat_history,
                    session_context=session_context,
                ))
                response_text = result.answer
                tool_traces = [t.to_history_entry() for t in result.traces]

            # 4. Escalonamento — apenas quando o Router direcionou explicitamente
            if router_result.agent == "escalation":
                # Detecta se é uma reclamação de cliente
                import re as _re
                is_reclamacao = bool(_re.search(
                    r'reclama[çc][aã]o|reclamar|insatisfei|procon|cancelar|cancela[çc][aã]o|estorno|reembolso|devolu[çc][aã]o|processo|processar',
                    user_message, _re.IGNORECASE
                ))
                # Extrai pedido_id do texto independentemente do tipo
                m = _re.search(r'\b(P\d+)\b', user_message, _re.IGNORECASE)
                pedido_id_inline = m.group(1).upper() if m else None

                esc = self.escalation.run(EscalationInput(
                    situation=user_message,
                    evidence=user_message,
                    triggered_by="router",
                    client_plan=None,
                    tipo="reclamacao" if is_reclamacao else None,
                    pedido_id=pedido_id_inline,
                    colaborador_nome=user_name,
                    colaborador_email=user_email,
                ))

                # Se o agente precisa de mais informação (ex: pedido_id não informado)
                if esc.needs_more_info:
                    self._pending_reclamacao = {
                        "situation":       user_message,
                        "evidence":        user_message,
                        "triggered_by":    "router",
                        "mensagem_original": user_message,
                    }
                    response_text = esc.question or "Para registrar a reclamação, qual é o número do pedido?"
                else:
                    registrar_escalamento(
                        session_id=session_id,
                        user_id=user_id,
                        mensagem_usuario=user_message,
                        nivel=esc.level,
                        motivo=esc.reason,
                        evidencia=esc.evidence,
                        proximos_passos=esc.next_steps,
                        triggered_by="router",
                        user_name=user_name,
                        user_email=user_email,
                        plano=None,
                        pedido_id=esc.pedido_id,
                        tipo=esc.tipo,
                    )
                    if is_reclamacao:
                        response_text = (
                            f"Reclamação registrada com sucesso para o pedido {esc.pedido_id}. "
                            f"O time responsável será acionado. "
                            f"Número de protocolo: ESC-{session_id[-6:].upper()}."
                        )
                    else:
                        response_text = _MENSAGEM_ESCALONAMENTO

            agent_selected = router_result.agent

        except RateLimitError:
            self.chat_history.append({"role": "user",      "content": user_message,        "agent_selected": "rate_limit"})
            self.chat_history.append({"role": "assistant",  "content": MENSAGEM_RATE_LIMIT, "agent_selected": "rate_limit"})
            return MENSAGEM_RATE_LIMIT, "rate_limit"

        # 5. Atualiza histórico — ordem: user → tools → assistant
        self.chat_history.append({
            "role":           "user",
            "content":        user_message,
            "agent_selected": agent_selected,
        })
        for trace_entry in tool_traces:
            self.chat_history.append(trace_entry)
        self.chat_history.append({
            "role":           "assistant",
            "content":        response_text,
            "agent_selected": agent_selected,
        })

        return response_text, agent_selected
