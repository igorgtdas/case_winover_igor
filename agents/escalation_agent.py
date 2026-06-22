"""
================================================================================
Escalation Agent — Especialista em Escalonamento
================================================================================

O QUE É:
    Agente acionado em situações críticas que requerem intervenção humana.
    Pode ser chamado de dois caminhos distintos:
      1. Stop-checker do Guard (guard_agent detectou should_escalate=True)
      2. Router direcionou explicitamente para escalation

PARA QUE SERVE:
    Avaliar a situação, classificar o nível de urgência e gerar um relatório
    estruturado com motivo, evidência e próximos passos para o time humano.
    O usuário (colaborador) NÃO vê o relatório — recebe apenas uma mensagem
    padrão de redirecionamento.

    Níveis de escalonamento:
      L1 → suporte operacional (dúvidas, status, FAQ)
      L2 → operações (conflitos de regra, cancelamento sensível)
      Financeiro → cobrança duplicada, estorno, chargeback
      Risco → fraude, comportamento suspeito, declaração criminosa

O QUE USA:
    - LangChain (ChatPromptTemplate + JsonOutputParser)
    - build_llm() de core/config.py (llama-3.3-70b-versatile, temperature=0)
    - core/knowledge_loader.py → playbook de escalonamento injetado no prompt
    - É STATELESS: recebe contexto pronto do Orchestrator (context_window=0)

COM QUEM CONVERSA:
    ← Recebe de: Orchestrator (dois caminhos: via Guard ou via Router)
    → Retorna para: Orchestrator com EscalationOutput (level, reason, next_steps)
    → Orchestrator persiste o resultado em core/escalation_log.py (banco SQLite)

================================================================================
Especialidade: avaliar se a situação requer atendimento humano e gerar relatório estruturado.

Parâmetros configuráveis via .env:
    ESCALATION_MODEL, ESCALATION_TEMPERATURE, ESCALATION_TOP_P, ESCALATION_MAX_TOKENS
    ESCALATION_CONTEXT_WINDOW (padrão 0 — recebe contexto pronto do orquestrador)

Input:
    EscalationInput(
        situation:    str,           # descrição da situação
        evidence:     str,           # evidência encontrada (resposta do agente anterior)
        client_id:    str | None,
        client_plan:  str | None,    # "Essencial" | "Pro" | "Enterprise"
        triggered_by: str | None     # "data_agent" | "knowledge_agent" | "user" | "guard"
    )

Output:
    EscalationOutput(
        should_escalate: bool,
        level:           "L1" | "L2" | "Financeiro" | "Risco" | "none",
        reason:          str,
        evidence:        str,
        next_steps:      str
    )

Níveis de escalonamento (conforme playbook_escalonamento.md):
    L1 / suporte operacional  → dúvidas simples, status, orientação FAQ
    L2 / operações            → conflitos de regra, cancelamento sensível, casos financeiros
    Financeiro                → cobrança duplicada confirmada, estorno, reconciliação
    Risco                     → fraude, chargeback, comportamento suspeito
"""

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.config import ESCALATION_PARAMS, build_llm
from core.knowledge_loader import load_all_docs


class EscalationInput(BaseModel):
    situation: str
    evidence: str
    client_id: str | None = None
    client_plan: str | None = None
    triggered_by: str | None = None
    pedido_id: str | None = None        # número do pedido (reclamação)
    colaborador_nome: str | None = None  # nome do colaborador (SessionContext)
    colaborador_email: str | None = None # email do colaborador (SessionContext)
    tipo: str | None = None              # "reclamacao" | None


class EscalationOutput(BaseModel):
    should_escalate: bool
    level: str           # "L1" | "L2" | "Financeiro" | "Risco" | "none"
    reason: str
    evidence: str
    next_steps: str
    needs_more_info: bool = False  # True → não registrar, perguntar ao colaborador
    question: str | None = None   # pergunta ao colaborador quando needs_more_info=True
    pedido_id: str | None = None  # extraído da situação ou informado
    tipo: str | None = None       # "reclamacao" | None


_SYSTEM_PROMPT = """Você é o Atlas Escalation, especialista em análise e classificação de escalonamentos para o AtlasShop Assist, assistente interno de suporte da AtlasShop.
Sua missão é avaliar situações críticas e gerar um relatório estruturado para orientar o atendimento humano — com nível de urgência, motivo, evidência e próximos passos claros.

Tools:
- knowledge_base: políticas internas e playbook de escalonamento vigentes — use como referência para determinar nível e próximos passos

Safety:
1) Nunca minimize situações de risco — quando em dúvida entre dois níveis, escolha o mais alto.
2) Nunca invente evidências — use apenas o que foi informado em "situation" e "evidence".
3) Se a situação não justificar escalonamento (ex: dúvida simples roteada erroneamente), retorne should_escalate=false e level="none".
4) Os próximos passos devem ser objetivos e acionáveis — quem vai receber sabe o que fazer.
5) Para reclamações de cliente (tipo="reclamacao"): OBRIGATORIAMENTE inclua pedido_id no registro. Se pedido_id não foi informado, 
defina needs_more_info=true e question com a pergunta ao colaborador. NÃO registre sem pedido_id.

Input:
situation: descrição da situação que gerou o escalonamento
evidence: evidência ou resposta do agente anterior que justifica o escalonamento
triggered_by: guard_agent | router (quem acionou o escalonamento)
tipo: "reclamacao" quando for uma reclamação formal de cliente | null para outros escalonamentos
pedido_id: número do pedido relacionado (pode ser null se ainda não informado)
colaborador_nome: nome do colaborador que está registrando
colaborador_email: email do colaborador que está registrando

Output:
JSON válido, sem markdown, sem texto adicional:
{{
  "should_escalate": true,
  "level": "L1"|"L2"|"Financeiro"|"Risco"|"none",
  "reason": "<motivo objetivo e conciso>",
  "evidence": "<evidência que justifica>",
  "next_steps": "<ação específica para o time humano>",
  "needs_more_info": false,
  "question": null,
  "pedido_id": "<id do pedido ou null>",
  "tipo": "<reclamacao ou null>"
}}

Se needs_more_info=true, os campos should_escalate/level/reason/evidence/next_steps podem ter valores provisórios — o registro só ocorre quando needs_more_info=false.

Exemplos:


Reclamação sem pedido_id informado → 
{{
"should_escalate":true,"level":"L1","reason":"Reclamação formal de cliente",
"evidence":"Colaborador reportou reclamação sem informar o pedido",
"next_steps":"Aguardando número do pedido","needs_more_info":true,
"question":"Para registrar a reclamação, preciso do número do pedido. Qual é o ID do pedido relacionado à reclamação?","pedido_id":null,"tipo":"reclamacao"}}

Reclamação com pedido_id=P1003 → {{"should_escalate":true,"level":"L1","reason":"Reclamação formal do cliente referente ao pedido P1003","evidence":"Colaborador registrou reclamação do cliente sobre o pedido P1003","next_steps":"Encaminhar reclamação para time de Atendimento com histórico do pedido P1003","needs_more_info":false,"question":null,"pedido_id":"P1003","tipo":"reclamacao"}}

Situação: pedido P1008 com status_pagamento=fraud_review → 
{{"should_escalate":true,
"level":"Risco","reason":"Pedido em fraud_review sem resolução",
"evidence":"P1008 status_pagamento=fraud_review desde 2026-03-26",
"next_steps":"Encaminhar para time de Risco com histórico completo do pedido P1008 e cliente C008","needs_more_info":false,
"question":null,"pedido_id":"P1008","tipo":null}}

Situação: atendente perguntou qual o horário de suporte → 
{{"should_escalate":false,"level":"none","reason":"Dúvida operacional simples — não requer escalonamento",
"evidence":"Pergunta sobre horário de atendimento",
"next_steps":"Redirecionar para knowledge_agent","needs_more_info":false,
"question":null,"pedido_id":null,"tipo":null}}

Situação: pedido P0877 com status_pagamento=chargeback, cliente questiona cancelamento →
{{"should_escalate":true,
"level":"Financeiro","reason":"Pagamento com chargeback ativo requer análise de disputas",
"evidence":"P0877 status_pagamento=chargeback, cliente C019 relata não ter solicitado cancelamento",
"next_steps":"Encaminhar para time Financeiro com comprovante de pagamento e histórico do pedido P0877","needs_more_info":false,
"question":null,"pedido_id":"P0877","tipo":"chargeback"}}

Situação: cliente solicita troca no 8º dia (política: 7 dias), alega produto com defeito →
{{"should_escalate":true,
"level":"Comercial","reason":"Solicitação fora da política de troca com possível exceção por defeito de fabricação",
"evidence":"Cliente C055 solicita troca no dia 8, prazo máximo é 7 dias, relato de defeito no produto",
"next_steps":"Acionar time Comercial para avaliar exceção, solicitar foto do defeito ao cliente","needs_more_info":true,
"question":"Você pode enviar uma foto ou vídeo mostrando o defeito no produto?","pedido_id":null,"tipo":"excecao_politica"}}

Fallback:
Se não houver evidência suficiente para determinar o nível com segurança, use level="L2" e oriente o time humano a investigar antes de escalar mais.

Tone:
Técnico, objetivo e acionável. O relatório será lido por um atendente humano sob pressão — seja direto e sem ambiguidade.

Playbook e políticas vigentes:
{knowledge_base}"""


class EscalationAgent:
    def __init__(self):
        self.llm = build_llm(ESCALATION_PARAMS)
        self.knowledge_base = load_all_docs()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", (
                "Situação: {situation}\n"
                "Evidência: {evidence}\n"
                "Cliente: {client_id} | Plano: {client_plan}\n"
                "Originado por: {triggered_by}\n"
                "Tipo: {tipo}\n"
                "Pedido ID: {pedido_id}\n"
                "Colaborador: {colaborador_nome} ({colaborador_email})"
            )),
        ])
        self.parser = JsonOutputParser(pydantic_object=EscalationOutput)
        self.chain = self.prompt.partial(knowledge_base=self.knowledge_base) | self.llm | self.parser

    def run(self, input_data: EscalationInput) -> EscalationOutput:
        result = self.chain.invoke({
            "situation":        input_data.situation,
            "evidence":         input_data.evidence,
            "client_id":        input_data.client_id         or "N/A",
            "client_plan":      input_data.client_plan        or "N/A",
            "triggered_by":     input_data.triggered_by       or "N/A",
            "tipo":             input_data.tipo                or "N/A",
            "pedido_id":        input_data.pedido_id           or "não informado",
            "colaborador_nome":  input_data.colaborador_nome   or "N/A",
            "colaborador_email": input_data.colaborador_email  or "N/A",
        })
        return EscalationOutput(**result)
