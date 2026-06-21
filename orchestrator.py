"""
Orchestrator — Controlador principal do fluxo conversacional

Fluxo por mensagem:
  1. GuardAgent      → checa segurança e safety → block? retorna rejeição
  2. RouterAgent     → classifica intenção → knowledge | data | escalation
  3. Agente alvo     → KnowledgeAgent | DataAgent | EscalationAgent
  4. Se should_escalate → EscalationAgent gera relatório estruturado
  5. Retorna resposta final ao usuário
"""

import logging

from agents.guard_agent      import GuardAgent,      GuardInput
from agents.router_agent     import RouterAgent,     RouterInput
from agents.knowledge_agent  import KnowledgeAgent,  KnowledgeInput
from agents.data_agent       import DataAgent,       DataInput
from agents.escalation_agent import EscalationAgent, EscalationInput

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.guard      = GuardAgent()
        self.router     = RouterAgent()
        self.knowledge  = KnowledgeAgent()
        self.data       = DataAgent()
        self.escalation = EscalationAgent()
        self.chat_history: list[dict] = []

    def chat(self, user_message: str, user_id: str = "user", session_id: str = "default") -> str:
        # 1. Guard
        try:
            guard_result = self.guard.run(GuardInput(
                content=user_message,
                user_id=user_id,
                session_id=session_id,
            ))
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("Unexpected error in guard step (session=%s): %s", session_id, exc)
            raise RuntimeError(f"Guard step failed: {exc}") from exc

        if guard_result.action == "block":
            return f"[{guard_result.category.upper()}] Mensagem bloqueada: {guard_result.reason}"

        # 2. Router
        try:
            router_result = self.router.run(RouterInput(
                content=user_message,
                chat_history=self.chat_history,
            ))
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("Unexpected error in router step (session=%s): %s", session_id, exc)
            raise RuntimeError(f"Router step failed: {exc}") from exc

        # 3. Agente alvo
        response_text = ""
        should_escalate = False
        escalation_context: dict = {}

        if router_result.agent == "knowledge":
            result = self.knowledge.run(KnowledgeInput(
                question=user_message,
                chat_history=self.chat_history,
            ))
            response_text = result.answer
            should_escalate = result.should_escalate
            escalation_context = {
                "situation":    user_message,
                "evidence":     result.answer,
                "triggered_by": "knowledge_agent",
            }

        elif router_result.agent == "data":
            result = self.data.run(DataInput(
                question=user_message,
                chat_history=self.chat_history,
            ))
            response_text = result.answer
            should_escalate = result.should_escalate
            escalation_context = {
                "situation":    user_message,
                "evidence":     result.answer,
                "triggered_by": "data_agent",
            }

        elif router_result.agent == "escalation":
            should_escalate = True
            escalation_context = {
                "situation":    user_message,
                "evidence":     user_message,
                "triggered_by": "user",
            }

        else:
            logger.error(
                "Router returned unhandled agent=%r (session=%s), treating as knowledge",
                router_result.agent, session_id,
            )
            result = self.knowledge.run(KnowledgeInput(
                question=user_message,
                chat_history=self.chat_history,
            ))
            response_text = result.answer
            should_escalate = result.should_escalate
            escalation_context = {
                "situation":    user_message,
                "evidence":     result.answer,
                "triggered_by": "knowledge_agent",
            }

        # 4. Escalonamento
        if should_escalate:
            try:
                esc = self.escalation.run(EscalationInput(**escalation_context))
                escalation_block = (
                    f"\n\n--- ESCALONAMENTO NECESSÁRIO ---\n"
                    f"Nível:           {esc.level}\n"
                    f"Motivo:          {esc.reason}\n"
                    f"Evidência:       {esc.evidence}\n"
                    f"Próximos passos: {esc.next_steps}\n"
                    f"--------------------------------"
                )
                response_text = (response_text or "") + escalation_block
            except Exception as exc:
                logger.error("EscalationAgent failed (session=%s): %s", session_id, exc)
                response_text = (response_text or "") + (
                    "\n\n[ERRO] Não foi possível gerar o relatório de escalonamento. "
                    "Por favor, encaminhe manualmente para o time responsável."
                )

        # 5. Atualiza histórico
        self.chat_history.append({"role": "user",      "content": user_message})
        self.chat_history.append({"role": "assistant",  "content": response_text})

        return response_text
