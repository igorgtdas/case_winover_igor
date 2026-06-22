"""
================================================================================
Data Agent — Especialista em Dados Operacionais (SQL)
================================================================================

O QUE É:
    Agente especialista acionado quando a mensagem envolve consulta a registros
    específicos do banco: pedidos, clientes ou reembolsos identificados por ID,
    nome ou CPF.

PARA QUE SERVE:
    Responder perguntas operacionais em duas etapas:
      1. LLM converte a pergunta em uma query SELECT segura (apenas leitura)
      2. SQLAlchemy executa a query no SQLite; LLM interpreta o resultado em
         linguagem natural, alertando para status críticos (fraud_review, chargeback)

O QUE USA:
    - LangChain (ChatPromptTemplate + MessagesPlaceholder + StrOutputParser)
    - build_llm() de core/config.py (llama-3.3-70b-versatile, temperature=0)
    - core/database.py → SQLAlchemy engine conectado ao atlasshop.db (SQLite)
    - core/knowledge_loader.py → contexto de regras injetado no prompt de interpretação
    - tools/clock_tool.py → data atual para calcular "há quantos dias"
    - core/session_context.py → nome do colaborador na resposta
    - core/trace.py → registra clock_tool e sql_query no histórico
    - LangSmith (@traceable) → rastreamento de execução da query

COM QUEM CONVERSA:
    ← Recebe de: Orchestrator (quando RouterAgent retorna agent="data")
    → Retorna para: Orchestrator com DataOutput (answer, sql_used, traces)
    → Não chama outros agentes; decisão de escalonamento cabe ao Guard/Router

================================================================================
Dois passos:
  1. LLM gera SQL a partir da pergunta
  2. SQLAlchemy executa; LLM interpreta o resultado

Decisao de escalonamento: exclusivamente do Guard e do Router.
"""

import re
import logging

from pydantic import BaseModel
from sqlalchemy import text
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from core.config import DATA_PARAMS, build_llm
from core.database import get_engine
from core.knowledge_loader import load_all_docs
from core.session_context import SessionContext
from core.trace import ToolCall
from tools.clock_tool import hoje_brasilia
from langsmith import traceable

logger = logging.getLogger(__name__)


class DataInput(BaseModel):
    question: str
    chat_history: list[dict] = []
    session_context: SessionContext | None = None


class DataOutput(BaseModel):
    answer: str
    sql_used: str | None = None
    traces: list[ToolCall] = []


_SQL_PROMPT = """Você é o Atlas SQL, especialista em geração de queries SQLite para o banco operacional da AtlasShop.
Sua missão é converter a pergunta do atendente em uma query SELECT precisa e segura.

Safety Rules
1) Gere APENAS queries SELECT. Nunca INSERT, UPDATE, DELETE ou DDL.
2) Nunca invente nomes de colunas ou tabelas — use apenas o schema abaixo.
3) Se a pergunta não puder ser respondida com o schema disponível, gere: SELECT 'informacao_nao_disponivel_no_banco'


Input:
Pergunta em linguagem natural do atendente de suporte.


Output:
SQL puro em uma linha. Sem markdown, sem blocos de código, sem explicações, sem ponto-e-vírgula no final.


Exemplos:

Entrada: "qual o status do pedido P1003?" → SELECT pedido_id, status_pedido, status_pagamento FROM pedidos WHERE pedido_id = 'P1003'
Entrada: "E qual é o canal de origem desse pedido?" → SELECT canal_origem FROM pedidos WHERE pedido_id = 'avaliar numero do pedido no histórico'
Entrada: "o cliente C005 tem reembolso aberto?" → SELECT r.reembolso_id, r.status_reembolso, r.valor_brl FROM reembolsos r JOIN pedidos p ON r.pedido_id = p.pedido_id WHERE p.cliente_id = 'C005'
Entrada: "quais pedidos estão em fraud_review?" → SELECT pedido_id, cliente_id, valor_brl, ultimo_evento_em FROM pedidos WHERE status_pagamento = 'fraud_review'


Fallback:
Se a pergunta envolver regras de negócio que você não consegue resolver (ex: "está no prazo?", "pode cancelar?", "tem direito a reembolso?"),
busque os dados brutos do pedido/cliente/reembolso mencionado — datas, status, valores — para que a etapa seguinte possa aplicar as regras.
Exemplo: "pedido P1005 está dentro do prazo?" → SELECT pedido_id, status_pedido, status_pagamento, data_ativacao, data_cancelamento, ultimo_evento_em FROM pedidos WHERE pedido_id = 'P1005'

Somente retorne SELECT 'informacao_nao_disponivel_no_banco' se nenhum identificador (pedido, cliente, reembolso) for mencionado e a pergunta não puder ser respondida com o schema.


Schema disponível (SQLite):
- clientes   (cliente_id, nome_cliente, segmento, plano, cidade, estado, mrr_brl, status_cliente, data_inicio, owner_cs)
- pedidos    (pedido_id, cliente_id, plano, ciclo, valor_brl, status_pedido, status_pagamento, data_ativacao, data_cancelamento, ultimo_evento_em, canal_origem, observacao_operacional)
- reembolsos (reembolso_id, pedido_id, status_reembolso, motivo, valor_brl, criado_em, atualizado_em, observacao)"""

_INTERPRET_PROMPT = """Você é o Atlas Data, especialista em interpretação de dados operacionais para o AtlasShop Assist, assistente interno de suporte da AtlasShop.
Sua missão é transformar o resultado bruto de uma query SQL em uma resposta clara, útil e contextualizada para o atendente.


Tools disponíveis:
- clock_tool: data de hoje em Brasília = {data_hoje} — use para calcular "há quantos dias", "faz quanto tempo", vigências
- sql_query: a query executada e o resultado bruto estão disponíveis abaixo
- knowledge_summary: contexto de negócio e regras operacionais disponíveis abaixo


Safety Rules
1) Interprete apenas os dados retornados — nunca invente ou extrapole registros.
2) Se o resultado for "Nenhum resultado encontrado" ou "informacao_nao_disponivel_no_banco", informe claramente.
3) Se já existir reembolso registrado, informe o status atual sem sugerir novo reembolso.
4) Se status_pagamento for fraud_review ou chargeback, sinalize claramente para o atendente.


Input:
Colaborador: {user_name} | Data de hoje: {data_hoje}
Contexto de negócio: {knowledge_summary}
IMPORTANTE: o histórico de conversa é apenas contexto. Sua resposta deve ser baseada exclusivamente no resultado SQL da pergunta atual, informado na mensagem do usuário.


Output:
Resposta em linguagem natural, clara e objetiva.
Para cálculos de tempo, use o formato: "X dias (desde dd/mm/aaaa)".


Exemplos
Resultado: status_pagamento=fraud_review → "Atenção: o pedido P1008 está em fraud_review. Recomendo acionar o time de Risco."
Resultado: reembolso criado_em=2026-06-12, data_hoje=22/06/2026 → "O reembolso foi aprovado há 10 dias (desde 12/06/2026)."
Resultado: vazio → "Não encontrei registros para essa consulta no banco de dados."


Fallback
Se o resultado do banco for vazio ou "informacao_nao_disponivel_no_banco", responda:
"Não encontrei registros para essa consulta. Verifique o identificador informado ou consulte o time responsável."

Tone:
Profissional e direto. Destaque alertas operacionais (fraud_review, chargeback, Enterprise) de forma visível.
"""


def _truncar_historico(chat_history: list[dict], context_window: int) -> list:
    if context_window == 0:
        return []
    apenas_conversa = [m for m in chat_history if m["role"] in ("user", "assistant")]
    fatia = apenas_conversa[-(context_window * 2):]
    mensagens = []
    for m in fatia:
        if m["role"] == "user":
            mensagens.append(HumanMessage(content=m["content"]))
        else:
            mensagens.append(AIMessage(content=m["content"]))
    return mensagens


def _extrair_sql(raw: str) -> str:
    sql = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip()
    return sql.strip("`").strip()


class DataAgent:
    def __init__(self):
        self.llm = build_llm(DATA_PARAMS)
        self.engine = get_engine()
        knowledge_summary = load_all_docs()

        # sql_chain recebe histórico para resolver referências ("esse pedido", "o mesmo cliente")
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system", _SQL_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{question}"),
        ])
        self.sql_chain = sql_prompt | self.llm | StrOutputParser()

        # interpret_chain recebe histórico para contexto de conversa, mas a resposta
        # deve ser baseada exclusivamente no resultado SQL atual (reforçado no prompt)
        interpret_prompt = ChatPromptTemplate.from_messages([
            ("system", _INTERPRET_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "Pergunta atual: {question}\nSQL executado: {sql}\nResultado do banco: {resultado}\n\nResponda APENAS com base no resultado acima. Não use respostas anteriores do histórico como resposta."),
        ]).partial(knowledge_summary=knowledge_summary)
        self.interpret_chain = interpret_prompt | self.llm | StrOutputParser()

    @traceable(name="sql_query", run_type="tool")
    def _executar_sql(self, sql: str) -> str:
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(sql)).fetchall()
            if not rows:
                return "Nenhum resultado encontrado."
            return "\n".join(str(row) for row in rows)
        except Exception as exc:
            logger.warning("DataAgent: erro ao executar SQL '%s': %s", sql, exc)
            return f"Erro ao executar a query: {exc}"

    def run(self, input_data: DataInput) -> DataOutput:
        historico = _truncar_historico(input_data.chat_history, DATA_PARAMS["context_window"])
        ctx = input_data.session_context
        traces: list[ToolCall] = []

        # Tool: clock_tool
        data_hoje = hoje_brasilia()
        traces.append(ToolCall(
            tool="clock_tool",
            agent="data_agent",
            input={},
            output=data_hoje,
        ))

        # Tool: sql_query — passo 1: gera SQL (com histórico para resolver referências)
        sql_raw = self.sql_chain.invoke({"question": input_data.question, "chat_history": historico})
        sql = _extrair_sql(sql_raw)
        logger.info("DataAgent: SQL gerado: %s", sql)

        # Tool: sql_query — passo 2: executa no banco
        resultado = self._executar_sql(sql)
        logger.info("DataAgent: resultado: %s", resultado[:200])
        traces.append(ToolCall(
            tool="sql_query",
            agent="data_agent",
            input={"sql": sql},
            output=resultado,
        ))

        raw = self.interpret_chain.invoke({
            "question":     input_data.question,
            "sql":          sql,
            "resultado":    resultado,
            "chat_history": historico,
            "user_name":    ctx.user_name if ctx else "colaborador",
            "data_hoje":    data_hoje,
        })

        return DataOutput(answer=raw, sql_used=sql, traces=traces)
