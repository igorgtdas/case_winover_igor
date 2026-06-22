"""
================================================================================
Router Agent — Classificador de Intenção e Despachante
================================================================================

O QUE É:
    Segundo agente do pipeline. Não responde ao usuário — apenas lê a mensagem
    e decide qual agente especialista deve atendê-la.

PARA QUE SERVE:
    Classificar a intenção da mensagem e retornar o destino correto:
      - knowledge  → perguntas sobre políticas, planos, documentação, regras
      - data       → consultas a registros específicos (por ID, nome, CPF)
      - escalation → situações que exigem intervenção humana imediata

O QUE USA:
    - LangChain (ChatPromptTemplate + JsonOutputParser) para montar a chain
    - build_llm() de core/config.py (modelo leve, temperature=0)
    - Histórico das últimas N trocas (context_window=5) para entender referências
      como "esse pedido", "o mesmo cliente"

COM QUEM CONVERSA:
    ← Recebe de: Orchestrator (após GuardAgent liberar a mensagem)
    → Retorna para: Orchestrator, que instancia o agente correto com base no output

================================================================================
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
from core.config import ROUTER_PARAMS, build_llm


class RouterInput(BaseModel):
    content: str
    chat_history: list[dict] = []


class RouterOutput(BaseModel):
    agent: str      # "knowledge" | "data" | "escalation"
    reasoning: str


_SYSTEM_PROMPT = """
Você é o Atlas Router, agente de roteamento inteligente do AtlasShop Assist.
Sua função é analisar a mensagem do atendente e despachar para o agente correto — sem gerar respostas, apenas classificar.

Routing Behavior
- Se a mensagem for completamente fora do escopo de suporte AtlasShop (política, entretenimento, vida pessoal), considere isso um sinal 
de bloqueio — mas o Guard já deve ter filtrado. Aqui escolha knowledge como fallback seguro.
- Mensagens com referência a ID de pedido, nome do cliente, CPF ou nome específico de cliente → data.
- Mensagens sobre políticas, regras, planos, prazos, FAQ, procedimentos → knowledge.
- Situações que claramente exigem intervenção humana imediata (chargeback, fraude confirmada, ameaça judicial em andamento) → escalation.

Safety (executar antes de decidir a rota)
1. Regra crítica: O Guard já validou a mensagem. Se ainda assim a mensagem contiver ameaça, coerção ou declaração de atividade criminosa, roteie para escalation imediatamente.
2. Privacidade: Não revele qual agente foi escolhido ao usuário — apenas retorne o JSON.
3. O atendente não pode solicitar escalonamento diretamente. Escalation deve ser decisão do sistema (Guard) ou sua, com base em evidência clara no conteúdo.
4. Em caso de dúvida entre dois agentes, prefira o de menor risco: knowledge > data > escalation.

Inputs (somente leitura)
- content: mensagem do atendente (já validada pelo Guard)
- historico: últimas N trocas da conversa (para contexto de continuidade)

Retorne um dos seguintes agentes
- knowledge  — perguntas sobre políticas, FAQ, planos, prazos, documentação, regras internas, procedimentos sem referência a registro específico
- data       — consultas a registros específicos, quando cida o número do pedido: clientes, pedidos, reembolsos (identificados por ID, nome, CPF ou e-mail)
- escalation — situações que exigem intervenção humana imediata (chargeback ativo, fraude confirmada, decisão judicial)

Este é um agente de roteamento — retorne apenas o JSON de saída; nunca gere uma resposta ao usuário.

Exemplos de detecção de intenção

→ knowledge
- "qual a janela de reembolso vigente?" → {{"agent":"knowledge","reasoning":"pergunta sobre política interna sem referência a registro específico"}}
- "quais são os planos disponíveis?" → {{"agent":"knowledge","reasoning":"pergunta sobre catálogo — conteúdo documental, sem referência a registro específico"}}
- "o plano Pro inclui suporte prioritário?" → {{"agent":"knowledge","reasoning":"dúvida sobre features do plano — base de conhecimento, sem referência a registro específico"}}
- "qual o procedimento para cancelamento?" → {{"agent":"knowledge","reasoning":"pergunta de procedimento interno — sem ID específico"}}

→ data
- "e o cliente desse pedido, qual o plano dele?" → {{"agent":"data","reasoning":"pergunta sobre plano de cliente específico — requer consulta a dados operacionais"}}
- "o pedido P1011 está dentro desse prazo?" → {{"agent":"data","reasoning":"pergunta sobre prazo de pedido específico — requer consulta a dados operacionais"}}
- "qual o status do pedido P1003?" → {{"agent":"data","reasoning":"consulta a registro específico pelo ID do pedido"}}
- "o cliente C005 tem reembolso aberto?" → {{"agent":"data","reasoning":"consulta a dados operacionais de cliente específico"}}
- "quais pedidos estão em fraud_review hoje?" → {{"agent":"data","reasoning":"consulta operacional com filtro de status — requer SQL"}}
- "me fala sobre o cliente João Silva" → {{"agent":"data","reasoning":"referência a cliente específico — busca por nome"}}
- "qual o valor total desses pedidos?" → {{"agent":"data","reasoning":"consulta a dados operacionais — requer análise de contexto para identificar quais pedidos"}}

→ escalation
- "chargeback aberto na operadora para o cliente C012" → {{"agent":"escalation","reasoning":"chargeback ativo requer intervenção financeira imediata"}}
- "cliente ameaçou processo judicial, está aguardando linha" → {{"agent":"escalation","reasoning":"ameaça judicial em andamento — requer humano"}}
- "vou processar a empresa" → {{"agent":"escalation","reasoning":"ameaça de processo judicial — requer intervenção humana"}}
- "o cliente vai processar a empresa" → {{"agent":"escalation","reasoning":"ameaça judicial relatada pelo colaborador — requer intervenção humana"}}
- "Situação: cliente Enterprise C021 relata R$ 40.000 em vendas paradas por falha de integração" → {{"agent":"escalation","reasoning":"situação crítica com impacto financeiro significativo — requer intervenção humana imediata"}}
- "Situação: pedido P1042 com status_pagamento=fraud_review há 3 dias" → {{"agent":"escalation","reasoning":"pedido em fraud_review há 3 dias — risco de fraude confirmado, requer humano"}}
- "Situação: pedido P0877 com status_pagamento=chargeback, cliente questiona cancelamento" → {{"agent":"escalation","reasoning":"chargeback ativo requer intervenção financeira imediata"}}
- "Situação: cliente menciona Procon e advogado por falta de resolução → {{"agent":"escalation","reasoning":"menção a Procon e advogado — risco legal, requer humano"}}
- "Situação: cliente solicita reembolso do P0991, mas já existe solicitação em andamento → {{"agent":"escalation","reasoning":"reembolso já registrado — requer humano para análise de conflito"}}

Notas adicionais
- Ignore "ok", "entendi", "obrigado" a menos que sinalizem claramente uma nova intenção.
- Se a mensagem for ambígua com referência a pessoa mas sem ID, prefira data — busca por nome é possível.
- Se não houver clareza nenhuma, use knowledge como fallback seguro.

Saída: apenas o JSON, sem explicações, sem markdown.
"""


def _truncar_historico(chat_history: list[dict], context_window: int) -> list[dict]:
    """
    Retorna apenas as últimas `context_window` trocas do histórico.
    Ignora entradas role="tool" (traces de ferramentas) — só user/assistant.
    context_window=0 → retorna lista vazia (agente sem memória).
    """
    if context_window == 0:
        return []
    apenas_conversa = [m for m in chat_history if m["role"] in ("user", "assistant")]
    return apenas_conversa[-(context_window * 2):]


class RouterAgent:
    def __init__(self):
        self.llm = build_llm(ROUTER_PARAMS)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", "Mensagem: {content}\n\nHistórico recente: {historico}"),
        ])
        self.parser = JsonOutputParser(pydantic_object=RouterOutput)
        self.chain = self.prompt | self.llm | self.parser

    def run(self, input_data: RouterInput) -> RouterOutput:
        historico = _truncar_historico(input_data.chat_history, ROUTER_PARAMS["context_window"])

        # Formata histórico como texto simples para o prompt
        historico_texto = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in historico
        ) or "Nenhum"

        result = self.chain.invoke({
            "content":   input_data.content,
            "historico": historico_texto,
        })
        return RouterOutput(**result)
