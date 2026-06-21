"""
Knowledge Agent — Especialista em base de conhecimento e políticas
Especialidade: responder perguntas sobre documentação interna da AtlasShop.

Parâmetros configuráveis via .env:
    KNOWLEDGE_MODEL, KNOWLEDGE_TEMPERATURE, KNOWLEDGE_TOP_P, KNOWLEDGE_MAX_TOKENS
    KNOWLEDGE_CONTEXT_WINDOW → quantas mensagens anteriores o agente recebe (padrão 5 turnos)

Input:
    KnowledgeInput(
        question:     str,
        chat_history: list[dict]   # [{"role": "user"|"assistant", "content": str}]
    )

Output:
    KnowledgeOutput(
        answer:            str,
        sources:           list[str],   # documentos usados na resposta
        should_escalate:   bool,
        escalation_reason: str | None
    )

Tools disponíveis:
    get_full_knowledge_base() -> str   # retorna todos os docs como texto
    get_document(doc_name: str) -> str # retorna um doc específico

Responsabilidades:
    - Responder com base nos documentos de knowledge/
    - Resolver conflitos entre docs (priorizar mais recente com status vigente)
    - Citar qual documento foi usado (campo sources)
    - Não aprovar exceções comerciais — orientar escalonamento
    - Sinalizar should_escalate quando a situação exigir validação humana

Formato esperado no final da resposta do LLM:
    FONTES: [doc1.md, doc2.md]
    ESCALAR: true/false
    MOTIVO_ESCALONAMENTO: <motivo ou N/A>
"""

import re

from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from core.config import KNOWLEDGE_PARAMS, GROQ_API_KEY
from core.knowledge_loader import load_all_docs
from tools.knowledge_tools import get_document, get_full_knowledge_base


class KnowledgeInput(BaseModel):
    question: str
    chat_history: list[dict] = []


class KnowledgeOutput(BaseModel):
    answer: str
    sources: list[str]
    should_escalate: bool
    escalation_reason: str | None = None


_SYSTEM_PROMPT = """
Você é o especialista em base de conhecimento do AtlasShop Assist.

## Documentos internos disponíveis:
{knowledge_base}

## Regras obrigatórias:
1. Cite sempre qual documento usou (inclua no final: FONTES: [lista dos .md])
2. Quando dois documentos conflitarem, use o mais recente com status "vigente" e informe qual descartou
3. Não aprove exceções comerciais — oriente escalonamento nesses casos
4. Ao final, inclua obrigatoriamente:
   FONTES: [arquivo1.md, arquivo2.md]
   ESCALAR: true/false
   MOTIVO_ESCALONAMENTO: <motivo detalhado ou N/A>

Use as tools disponíveis se precisar consultar um documento específico.
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


def _parse_agent_output(raw: str) -> KnowledgeOutput:
    """
    Extrai campos estruturados da resposta em texto livre do agente ReAct.

    O LLM é instruído a encerrar a resposta com:
        FONTES: [doc1.md, doc2.md]
        ESCALAR: true/false
        MOTIVO_ESCALONAMENTO: <motivo ou N/A>

    Esta função lê essas marcações com regex e popula o KnowledgeOutput.
    O campo `answer` recebe o texto completo para auditoria — considere limpar
    as marcações antes de exibir ao usuário se preferir uma resposta mais limpa.
    """

    # --- FONTES ---------------------------------------------------------------
    # Formato esperado: FONTES: [politica_cancelamento_reembolso_atual.md, faq_atendimento.md]
    sources: list[str] = []
    fontes_match = re.search(r"FONTES:\s*\[([^\]]+)\]", raw, re.IGNORECASE)
    if fontes_match:
        sources = [s.strip() for s in fontes_match.group(1).split(",") if s.strip()]

    # TODO: se sources estiver vazio, tentar extrair nomes de .md mencionados no texto

    # --- ESCALAR --------------------------------------------------------------
    # Formato esperado: ESCALAR: true  ou  ESCALAR: false
    should_escalate = False
    escalar_match = re.search(r"ESCALAR:\s*(true|false)", raw, re.IGNORECASE)
    if escalar_match:
        should_escalate = escalar_match.group(1).lower() == "true"

    # --- MOTIVO_ESCALONAMENTO -------------------------------------------------
    # Formato esperado: MOTIVO_ESCALONAMENTO: Cliente solicitou exceção comercial
    escalation_reason: str | None = None
    motivo_match = re.search(
        r"MOTIVO_ESCALONAMENTO:\s*(.+?)(?:\n|$)", raw, re.IGNORECASE
    )
    if motivo_match:
        motivo = motivo_match.group(1).strip()
        # Ignora o valor padrão "N/A"
        if motivo.upper() not in ("N/A", "NA", "NONE", ""):
            escalation_reason = motivo

    # TODO: remover as marcações do campo `answer` antes de exibir ao usuário:
    #   answer_limpo = re.sub(r"\n?(FONTES:|ESCALAR:|MOTIVO_ESCALONAMENTO:).+", "", raw).strip()

    return KnowledgeOutput(
        answer=raw,
        sources=sources,
        should_escalate=should_escalate,
        escalation_reason=escalation_reason,
    )


class KnowledgeAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=KNOWLEDGE_PARAMS["model"],
            api_key=GROQ_API_KEY,
            temperature=KNOWLEDGE_PARAMS["temperature"],
            max_tokens=KNOWLEDGE_PARAMS["max_tokens"],
        )
        self.tools = [get_full_knowledge_base, get_document]
        self.knowledge_base = load_all_docs()

        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT.format(knowledge_base=self.knowledge_base)),
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

    def run(self, input_data: KnowledgeInput) -> KnowledgeOutput:
        # Aplica a janela de contexto antes de passar o histórico ao executor
        historico = _truncar_historico(
            input_data.chat_history,
            KNOWLEDGE_PARAMS["context_window"],
        )

        result = self.executor.invoke({
            "input":        input_data.question,
            "chat_history": historico,
        })
        return _parse_agent_output(result["output"])
