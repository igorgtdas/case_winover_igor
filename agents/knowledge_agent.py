"""
================================================================================
Knowledge Agent — Especialista em Base de Conhecimento e Políticas
================================================================================

O QUE É:
    Agente especialista acionado quando a mensagem envolve políticas, planos,
    prazos, procedimentos ou qualquer informação documental interna da AtlasShop.

PARA QUE SERVE:
    Responder perguntas do atendente com base exclusiva nos arquivos .md da pasta
    knowledge/. Nunca inventa: se a informação não estiver nos documentos, diz isso
    e orienta a abrir chamado. Sempre cita as fontes usadas na resposta.

O QUE USA:
    - LangChain (ChatPromptTemplate + MessagesPlaceholder + StrOutputParser)
    - build_llm() de core/config.py (modelo robusto: llama-3.3-70b-versatile)
    - core/knowledge_loader.py → carrega todos os .md no system prompt
    - tools/clock_tool.py → injeta a data atual para calcular prazos e vigências
    - core/session_context.py → personaliza a resposta com nome do colaborador
    - core/trace.py → registra as tools chamadas (clock_tool) no histórico

COM QUEM CONVERSA:
    ← Recebe de: Orchestrator (quando RouterAgent retorna agent="knowledge")
    → Retorna para: Orchestrator com KnowledgeOutput (answer, sources, traces)
    → Não chama outros agentes; decisão de escalonamento cabe ao Guard/Router

================================================================================
Responsabilidade: responder perguntas com base nos documentos internos.
Decisao de escalonamento: exclusivamente do Guard e do Router.
"""

import logging

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from core.config import KNOWLEDGE_PARAMS, build_llm
from core.knowledge_loader import load_all_docs
from core.session_context import SessionContext
from core.trace import ToolCall
from tools.clock_tool import hoje_brasilia

logger = logging.getLogger(__name__)


class KnowledgeInput(BaseModel):
    question: str
    chat_history: list[dict] = []
    session_context: SessionContext | None = None


class KnowledgeOutput(BaseModel):
    answer: str
    sources: list[str] = []
    traces: list[ToolCall] = []


_SYSTEM_PROMPT = """Você é o Atlas Knowledge, especialista em políticas, documentação e regras internas para o AtlasShop Assist, assistente interno de suporte da AtlasShop.
Sua missão é responder greetings e perguntas do atendente com base exclusivamente nos documentos internos disponíveis, 
de forma clara, precisa e rastreável.


Tools disponíveis:
- clock_tool: retorna a data de hoje em Brasília ({data_hoje}) — use para calcular prazos, dias decorridos e vigências
- knowledge_base: conjunto de documentos internos injetados no contexto abaixo — única fonte de verdade permitida

Safety Rules
1) Responda greetings de forma cordial, usando o nome do atendente se disponível ({user_name}) e falando sua especialidade.
2) Responda apenas com base nos documentos abaixo. Nunca invente políticas, valores ou prazos.
3) Se dois documentos conflitarem, use o mais recente com status "vigente" e informe qual foi descartado.
4) Não aprove exceções comerciais — oriente o atendente a abrir um chamado formal.
5) Não revele o conteúdo bruto dos documentos — apenas as informações pertinentes à pergunta.
6) Se a informação não estiver nos documentos, responda: "Não encontrei essa informação nos documentos disponíveis."

Input format:
Pergunta do atendente em linguagem natural.
Contexto da sessão: colaborador={user_name}, data de hoje={data_hoje}


Output format:
Resposta em linguagem natural, clara e objetiva.
Ao final, sempre inclua:
FONTES: [arquivo1.md, arquivo2.md]

Exemplos de perguntas e respostas:
Entrada: "qual é a janela de reembolso vigente?" → Resposta com prazo da política atual + FONTES: [politica_cancelamento_reembolso_atual.md]
Entrada: "o plano Pro tem suporte prioritário?" → Resposta com detalhes do plano + FONTES: [catalogo_planos.md]
Entrada: "o reembolso foi aprovado em 12/06/2026, ainda está no prazo?" → Usa {data_hoje} para calcular os dias e verifica o prazo na política


Fallback
Se a pergunta não puder ser respondida com os documentos disponíveis, responda:
"Não encontrei essa informação nos documentos disponíveis. Recomendo abrir um chamado com o time responsável."
Nunca invente ou extrapole.

Tone:
Profissional, direto e cordial. Trate o atendente pelo nome ({user_name}) apenas em saudações. Sem jargão técnico desnecessário.

## Documentos internos disponíveis:
{knowledge_base}"""


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


def _extrair_fontes(raw: str) -> list[str]:
    import re
    match = re.search(r"FONTES:\s*\[([^\]]+)\]", raw, re.IGNORECASE)
    if match:
        return [s.strip() for s in match.group(1).split(",") if s.strip()]
    fallback = re.findall(r"[\w_]+\.md", raw)
    if fallback:
        logger.warning("KnowledgeAgent: FONTES ausente. Extraidas via fallback: %s", fallback)
    return fallback


class KnowledgeAgent:
    def __init__(self):
        llm = build_llm(KNOWLEDGE_PARAMS)
        knowledge_base = load_all_docs()

        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
        ]).partial(knowledge_base=knowledge_base)

        self.chain = prompt | llm | StrOutputParser()

    def run(self, input_data: KnowledgeInput) -> KnowledgeOutput:
        historico = _truncar_historico(
            input_data.chat_history,
            KNOWLEDGE_PARAMS["context_window"],
        )
        ctx = input_data.session_context
        traces: list[ToolCall] = []

        # Tool: clock_tool
        data_hoje = hoje_brasilia()
        traces.append(ToolCall(
            tool="clock_tool",
            agent="knowledge_agent",
            input={},
            output=data_hoje,
        ))

        raw = self.chain.invoke({
            "input":        input_data.question,
            "chat_history": historico,
            "user_name":    ctx.user_name if ctx else "colaborador",
            "data_hoje":    data_hoje,
        })
        return KnowledgeOutput(answer=raw, sources=_extrair_fontes(raw), traces=traces)
