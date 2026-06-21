"""
Data Agent — Especialista em dados operacionais (SQL)
Especialidade: consultar clientes, pedidos e reembolsos via SQL no SQLite.

Parâmetros configuráveis via .env:
    DATA_MODEL, DATA_TEMPERATURE, DATA_TOP_P, DATA_MAX_TOKENS
    DATA_CONTEXT_WINDOW → quantas mensagens anteriores o agente recebe (padrão 5 turnos)

Input:
    DataInput(
        question:     str,
        chat_history: list[dict]   # [{"role": "user"|"assistant", "content": str}]
    )

Output:
    DataOutput(
        answer:            str,
        sql_used:          str | None,    # última query SQL executada
        raw_data:          dict | None,   # dados brutos retornados
        should_escalate:   bool,
        escalation_reason: str | None
    )

Tools disponíveis (via SQLDatabaseToolkit):
    sql_db_list_tables(tool_input: "")  -> "clientes, pedidos, reembolsos"
    sql_db_schema(table_names: str)     -> "CREATE TABLE ..."
    sql_db_query(query: str)            -> resultado da query em texto
    sql_db_query_checker(query: str)    -> query validada ou erro

Tabelas disponíveis:
    clientes   (cliente_id, nome_cliente, segmento, plano, cidade, estado, mrr_brl, status_cliente, data_inicio, owner_cs)
    pedidos    (pedido_id, cliente_id, plano, ciclo, valor_brl, status_pedido, status_pagamento, data_ativacao, data_cancelamento, ultimo_evento_em, canal_origem, observacao_operacional)
    reembolsos (reembolso_id, pedido_id, status_reembolso, motivo, valor_brl, criado_em, atualizado_em, observacao)

Regras de negócio ao interpretar resultados:
    - status_pagamento = 'fraud_review'  → sinalizar escalonamento para Risco
    - status_pagamento = 'chargeback'    → sinalizar escalonamento para Financeiro
    - plano = 'Enterprise'               → prioridade alta na resposta
    - reembolso já existente para pedido → não sugerir abertura de novo

Formato esperado no final da resposta do LLM:
    ESCALAR: true/false
    NIVEL: Risco | Financeiro | L2 | none
    MOTIVO: <motivo ou N/A>
    SQL_USADO: <última query executada>
"""

from pydantic import BaseModel
from core.config import DATA_PARAMS
from core.knowledge_loader import load_all_docs
from core.chat_history import truncar_historico
from core.parsing import parse_escalar, parse_nivel, parse_motivo, parse_sql_usado
from core.react_agent_factory import create_react_executor
from tools.sql_tools import get_sql_tools


class DataInput(BaseModel):
    question: str
    chat_history: list[dict] = []


class DataOutput(BaseModel):
    answer: str
    sql_used: str | None = None
    raw_data: dict | None = None
    should_escalate: bool = False
    escalation_reason: str | None = None


_SYSTEM_PROMPT = """
Você é o especialista em dados operacionais do AtlasShop Assist.
Você tem acesso ao banco SQLite com as tabelas: clientes, pedidos, reembolsos.

## Contexto de negócio (políticas vigentes):
{knowledge_summary}

## Regras ao interpretar dados:
- status_pagamento = 'fraud_review'  → inclua no final: ESCALAR: true | NIVEL: Risco
- status_pagamento = 'chargeback'    → inclua no final: ESCALAR: true | NIVEL: Financeiro
- plano = 'Enterprise'               → destaque prioridade alta
- reembolso já existente             → informe o status atual, não sugira novo

## Formato obrigatório ao final da resposta:
ESCALAR: true/false
NIVEL: Risco | Financeiro | L2 | none
MOTIVO: <motivo detalhado ou N/A>
SQL_USADO: <última query SQL executada>
"""


def _parse_agent_output(raw: str) -> DataOutput:
    """
    Extrai campos estruturados da resposta em texto livre do agente ReAct.

    O LLM é instruído a encerrar a resposta com:
        ESCALAR: true/false
        NIVEL: Risco | Financeiro | L2 | none
        MOTIVO: <motivo ou N/A>
        SQL_USADO: <query>
    """
    should_escalate = parse_escalar(raw)
    nivel = parse_nivel(raw)
    motivo = parse_motivo(raw, field_name="MOTIVO")

    # Inclui o nível na razão para facilitar o escalonamento downstream
    escalation_reason: str | None = None
    if motivo:
        escalation_reason = f"[{nivel}] {motivo}" if nivel else motivo

    return DataOutput(
        answer=raw,
        sql_used=parse_sql_usado(raw),
        raw_data=None,
        should_escalate=should_escalate,
        escalation_reason=escalation_reason,
    )


class DataAgent:
    def __init__(self):
        self.tools = get_sql_tools()
        knowledge_summary = load_all_docs()

        self.executor = create_react_executor(
            params=DATA_PARAMS,
            system_prompt=_SYSTEM_PROMPT.format(knowledge_summary=knowledge_summary),
            tools=self.tools,
        )

    def run(self, input_data: DataInput) -> DataOutput:
        historico = truncar_historico(
            input_data.chat_history,
            DATA_PARAMS["context_window"],
        )

        result = self.executor.invoke({
            "input":        input_data.question,
            "chat_history": historico,
        })
        return _parse_agent_output(result["output"])
