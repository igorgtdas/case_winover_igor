"""
Router Agent — Classificador de intenção e despachante
Especialidade: decidir para qual agente encaminhar a mensagem.

Parâmetros configuráveis via .env:
    ROUTER_MODEL, ROUTER_TEMPERATURE, ROUTER_TOP_P, ROUTER_MAX_TOKENS
    ROUTER_CONTEXT_WINDOW → quantas mensagens anteriores considerar (padrão 5 turnos)

Input:
    RouterInput(content: str, chat_history: list[dict])

Output:
    RouterOutput(
        agent:     "knowledge" | "data" | "escalation",
        reasoning: str
    )

Critérios de roteamento:
    knowledge  → perguntas sobre políticas, FAQ, planos, regras, documentação
    data       → consultas de dados específicos (clientes, pedidos, reembolsos por ID/nome)
    escalation → situações que claramente requerem atendimento humano imediato
"""

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.config import ROUTER_PARAMS
from core.llm_factory import create_llm
from core.chat_history import truncar_historico, formatar_historico_texto


class RouterInput(BaseModel):
    content: str
    chat_history: list[dict] = []


class RouterOutput(BaseModel):
    agent: str      # "knowledge" | "data" | "escalation"
    reasoning: str


_SYSTEM_PROMPT = """
Você é o roteador do AtlasShop Assist. Classifique a mensagem e escolha o agente correto.

## Agentes disponíveis:

**knowledge** — perguntas sobre documentação, políticas e regras internas.
  Exemplos: "qual a janela de reembolso?", "quando devo escalar?", "quais são os planos?",
            "o que diz a política de cancelamento?"

**data** — consultas sobre dados operacionais de clientes, pedidos ou reembolsos específicos.
  Exemplos: "qual o status do pedido P1003?", "o cliente C005 tem reembolso aberto?",
            "me mostra os dados da Loja Aurora", "quais pedidos estão em fraud_review?"

**escalation** — situações que claramente precisam de atendimento humano imediato.
  Exemplos: "cliente ameaçando processar judicialmente", "fraude confirmada",
            "chargeback aberto na operadora"

Responda SOMENTE em JSON válido, sem markdown:
{{"agent": "knowledge", "reasoning": "usuário pergunta sobre política de reembolso"}}
"""


class RouterAgent:
    def __init__(self):
        self.llm = create_llm(ROUTER_PARAMS)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", "Mensagem: {content}\n\nHistórico recente: {historico}"),
        ])
        self.parser = JsonOutputParser(pydantic_object=RouterOutput)
        self.chain = self.prompt | self.llm | self.parser

    def run(self, input_data: RouterInput) -> RouterOutput:
        historico = truncar_historico(input_data.chat_history, ROUTER_PARAMS["context_window"])
        historico_texto = formatar_historico_texto(historico)

        result = self.chain.invoke({
            "content":   input_data.content,
            "historico": historico_texto,
        })
        return RouterOutput(**result)
