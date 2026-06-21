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

from pydantic import BaseModel
from core.config import KNOWLEDGE_PARAMS
from core.knowledge_loader import load_all_docs
from core.chat_history import truncar_historico
from core.parsing import parse_escalar, parse_fontes, parse_motivo
from core.react_agent_factory import create_react_executor
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


def _parse_agent_output(raw: str) -> KnowledgeOutput:
    """
    Extrai campos estruturados da resposta em texto livre do agente ReAct.

    O LLM é instruído a encerrar a resposta com:
        FONTES: [doc1.md, doc2.md]
        ESCALAR: true/false
        MOTIVO_ESCALONAMENTO: <motivo ou N/A>
    """
    return KnowledgeOutput(
        answer=raw,
        sources=parse_fontes(raw),
        should_escalate=parse_escalar(raw),
        escalation_reason=parse_motivo(raw, field_name="MOTIVO_ESCALONAMENTO"),
    )


class KnowledgeAgent:
    def __init__(self):
        self.tools = [get_full_knowledge_base, get_document]
        knowledge_base = load_all_docs()

        self.executor = create_react_executor(
            params=KNOWLEDGE_PARAMS,
            system_prompt=_SYSTEM_PROMPT.format(knowledge_base=knowledge_base),
            tools=self.tools,
        )

    def run(self, input_data: KnowledgeInput) -> KnowledgeOutput:
        historico = truncar_historico(
            input_data.chat_history,
            KNOWLEDGE_PARAMS["context_window"],
        )

        result = self.executor.invoke({
            "input":        input_data.question,
            "chat_history": historico,
        })
        return _parse_agent_output(result["output"])
