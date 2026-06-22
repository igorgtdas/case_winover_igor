"""
================================================================================
tools/clock_tool.py — Ferramenta de Data/Hora (Fuso Brasília)
================================================================================

O QUE É:
    Tool utilitária que retorna a data e hora atual no fuso horário de Brasília
    (America/Sao_Paulo). Não é um LangChain Tool/AgentExecutor — é uma função
    Python pura chamada diretamente pelos agentes.

PARA QUE SERVE:
    - Fornecer a data atual como variável {data_hoje} nos prompts dos agentes,
      permitindo que o LLM calcule diferenças de dias sem alucinar datas
    - Exemplos de uso no sistema:
        "O reembolso foi aprovado há 10 dias (desde 12/06/2026)."
        "O prazo de 7 dias venceu em 19/06/2026."

O QUE USA:
    - datetime + zoneinfo → cálculo de hora local sem bibliotecas externas
    - LangSmith (@traceable) → rastreamento da chamada como run_type="tool"
    - Nenhum LLM ou banco de dados

COM QUEM CONVERSA:
    ← Chamado por: agents/knowledge_agent.py e agents/data_agent.py
       (hoje_brasilia() é invocado no método run() antes de chamar o LLM)
    → Resultado injetado como {data_hoje} no prompt e registrado via core/trace.py

================================================================================
Clock Tool — Retorna data e hora atual no fuso horário de Brasília (America/Sao_Paulo).

Uso nos agentes:
    from tools.clock_tool import hoje_brasilia
    data_hoje = hoje_brasilia()   # "22/06/2026"

A data é injetada como variável {data_hoje} no prompt do agente, permitindo que o LLM
calcule diferenças de dias entre a data atual e datas vindas do banco de dados.

Não usa LangChain Tool/AgentExecutor — compatível com chains diretas (prompt | llm | parser).
"""

from datetime import datetime
import zoneinfo
from langsmith import traceable

_TZ_BRASILIA = zoneinfo.ZoneInfo("America/Sao_Paulo")


@traceable(name="clock_tool", run_type="tool")
def hoje_brasilia() -> str:
    """Retorna a data de hoje em Brasília no formato dd/mm/aaaa."""
    return datetime.now(_TZ_BRASILIA).strftime("%d/%m/%Y")


@traceable(name="clock_tool_datetime", run_type="tool")
def agora_brasilia() -> str:
    """Retorna data e hora atual em Brasília no formato dd/mm/aaaa HH:MM."""
    return datetime.now(_TZ_BRASILIA).strftime("%d/%m/%Y %H:%M")
