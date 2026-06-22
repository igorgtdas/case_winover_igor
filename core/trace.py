"""
================================================================================
core/trace.py — Contrato de Rastreamento de Chamadas de Tools
================================================================================

O QUE É:
    Define o modelo ToolCall — estrutura de dados que registra cada chamada de
    ferramenta feita por um agente durante o processamento de uma mensagem.

PARA QUE SERVE:
    - Padronizar como os agentes reportam o uso de tools (clock_tool, sql_query)
    - Permitir que o Orchestrator anexe esses registros ao histórico da sessão
      com role="tool", tornando as chamadas visíveis em GET /session/{id}/history
    - Os registros são ignorados pelo _truncar_historico() dos agentes (filtro
      user/assistant apenas), portanto não poluem o contexto enviado ao LLM

O QUE USA:
    - Pydantic BaseModel → validação e serialização do modelo
    - Nenhum LLM, banco ou arquivo externo

COM QUEM CONVERSA:
    ← Usado por: agents/knowledge_agent.py e agents/data_agent.py (criam ToolCall)
    → Consumido por: Orchestrator (recebe lista de ToolCall via result.traces e
       os adiciona ao chat_history com to_history_entry())

================================================================================
Contrato de rastreamento de chamadas de ferramentas (tools).

Cada tool chamada por um agente gera um ToolCall registrado no histórico da sessão
com role="tool". Esses registros ficam visíveis em GET /session/{id}/history
mas são ignorados pelo _truncar_historico (que filtra só user/assistant),
portanto não poluem o contexto enviado ao LLM.

Schema de uma entrada no histórico:
    {
        "role":   "tool",
        "agent":  "data_agent" | "knowledge_agent" | ...,
        "tool":   "clock_tool" | "sql_query" | ...,
        "input":  { ... },   # argumentos passados à tool
        "output": { ... }    # retorno da tool
    }
"""

from pydantic import BaseModel
from typing import Any


class ToolCall(BaseModel):
    tool: str            # nome da tool
    agent: str           # agente que fez a chamada
    input: dict[str, Any]   # argumentos de entrada
    output: Any          # retorno (string, dict, lista, etc.)

    def to_history_entry(self) -> dict:
        return {
            "role":   "tool",
            "agent":  self.agent,
            "tool":   self.tool,
            "input":  self.input,
            "output": self.output,
        }
