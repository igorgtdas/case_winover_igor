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

import re

from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from core.config import DATA_PARAMS, GROQ_API_KEY
from core.knowledge_loader import load_all_docs
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


def _truncar_historico(chat_history: list[dict], context_window: int) -> list[dict]:
    """
    Retorna apenas as últimas `context_window` trocas do histórico.
    Cada troca = 2 mensagens (user + assistant).
    context_window=0 → retorna lista vazia.
    """
    if context_window == 0:
        return []
    return chat_history[-(context_window * 2):]


def _parse_agent_output(raw: str) -> DataOutput:
    """
    Extrai campos estruturados da resposta em texto livre do agente ReAct.

    O LLM é instruído a encerrar a resposta com:
        ESCALAR: true/false
        NIVEL: Risco | Financeiro | L2 | none
        MOTIVO: <motivo ou N/A>
        SQL_USADO: <query>

    Esta função lê essas marcações com regex e popula o DataOutput.
    """

    # --- ESCALAR --------------------------------------------------------------
    # Formato esperado: ESCALAR: true  ou  ESCALAR: false
    should_escalate = False
    escalar_match = re.search(r"ESCALAR:\s*(true|false)", raw, re.IGNORECASE)
    if escalar_match:
        should_escalate = escalar_match.group(1).lower() == "true"

    # --- NIVEL ----------------------------------------------------------------
    # Usado apenas para compor o motivo de escalonamento
    # Formato esperado: NIVEL: Risco
    nivel: str | None = None
    nivel_match = re.search(
        r"NIVEL:\s*(Risco|Financeiro|L2|L1|none)", raw, re.IGNORECASE
    )
    if nivel_match:
        nivel = nivel_match.group(1).strip()

    # --- MOTIVO ---------------------------------------------------------------
    # Formato esperado: MOTIVO: Pedido em fraud_review
    escalation_reason: str | None = None
    motivo_match = re.search(r"MOTIVO:\s*(.+?)(?:\n|$)", raw, re.IGNORECASE)
    if motivo_match:
        motivo = motivo_match.group(1).strip()
        if motivo.upper() not in ("N/A", "NA", "NONE", ""):
            # Inclui o nível na razão para facilitar o escalonamento downstream
            escalation_reason = f"[{nivel}] {motivo}" if nivel else motivo

    # --- SQL_USADO ------------------------------------------------------------
    # Formato esperado: SQL_USADO: SELECT * FROM pedidos WHERE ...
    sql_used: str | None = None
    sql_match = re.search(r"SQL_USADO:\s*(.+?)(?:\n\n|$)", raw, re.IGNORECASE | re.DOTALL)
    if sql_match:
        sql_candidate = sql_match.group(1).strip()
        # Ignora valores vazios ou "N/A"
        if sql_candidate.upper() not in ("N/A", "NA", "NONE", ""):
            sql_used = sql_candidate

    # TODO: remover as marcações do campo `answer` antes de exibir ao usuário:
    #   answer_limpo = re.sub(r"\n?(ESCALAR:|NIVEL:|MOTIVO:|SQL_USADO:).+", "", raw).strip()

    return DataOutput(
        answer=raw,
        sql_used=sql_used,
        raw_data=None,  # TODO: popular com resultado bruto da última query se necessário
        should_escalate=should_escalate,
        escalation_reason=escalation_reason,
    )


class DataAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=DATA_PARAMS["model"],
            api_key=GROQ_API_KEY,
            temperature=DATA_PARAMS["temperature"],
            max_tokens=DATA_PARAMS["max_tokens"],
        )
        self.tools = get_sql_tools()
        self.knowledge_summary = load_all_docs()

        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT.format(knowledge_summary=self.knowledge_summary)),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_react_agent(self.llm, self.tools, prompt)
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=10,
        )

    def run(self, input_data: DataInput) -> DataOutput:
        # Aplica a janela de contexto antes de passar o histórico ao executor
        historico = _truncar_historico(
            input_data.chat_history,
            DATA_PARAMS["context_window"],
        )

        result = self.executor.invoke({
            "input":        input_data.question,
            "chat_history": historico,
        })
        return _parse_agent_output(result["output"])
