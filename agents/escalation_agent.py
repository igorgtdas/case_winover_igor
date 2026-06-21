"""
Escalation Agent — Especialista em escalonamento
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

import logging

from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.config import ESCALATION_PARAMS, GROQ_API_KEY
from core.knowledge_loader import load_all_docs

logger = logging.getLogger(__name__)


class EscalationInput(BaseModel):
    situation: str
    evidence: str
    client_id: str | None = None
    client_plan: str | None = None
    triggered_by: str | None = None


class EscalationOutput(BaseModel):
    should_escalate: bool
    level: str       # "L1" | "L2" | "Financeiro" | "Risco" | "none"
    reason: str
    evidence: str
    next_steps: str


_SYSTEM_PROMPT = """
Você é o especialista em escalonamento do AtlasShop Assist.

## Base de conhecimento (políticas e playbook vigentes):
{knowledge_base}

Analise a situação e determine:
1. Se requer escalonamento humano (should_escalate)
2. Qual nível: L1, L2, Financeiro, Risco, ou none (não requer)
3. Motivo objetivo
4. Evidência que justifica
5. Próximos passos para o atendente humano

Responda SOMENTE em JSON válido, sem markdown:
{{
  "should_escalate": true,
  "level": "Risco",
  "reason": "Pedido em fraud_review sem resolução",
  "evidence": "P1008 com status_pagamento=fraud_review desde 2026-03-26",
  "next_steps": "Encaminhar para time de Risco com os dados do pedido P1008 e histórico do cliente C008"
}}
"""


class EscalationAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=ESCALATION_PARAMS["model"],
            api_key=GROQ_API_KEY,
            temperature=ESCALATION_PARAMS["temperature"],
            max_tokens=ESCALATION_PARAMS["max_tokens"],
        )
        self.knowledge_base = load_all_docs()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT.format(knowledge_base=self.knowledge_base)),
            ("human", (
                "Situação: {situation}\n"
                "Evidência: {evidence}\n"
                "Cliente: {client_id} | Plano: {client_plan}\n"
                "Originado por: {triggered_by}"
            )),
        ])
        self.parser = JsonOutputParser(pydantic_object=EscalationOutput)
        self.chain = self.prompt | self.llm | self.parser

    def run(self, input_data: EscalationInput) -> EscalationOutput:
        # EscalationAgent é stateless — o contexto já chega condensado via EscalationInput
        try:
            result = self.chain.invoke({
                "situation":    input_data.situation,
                "evidence":     input_data.evidence,
                "client_id":    input_data.client_id    or "N/A",
                "client_plan":  input_data.client_plan  or "N/A",
                "triggered_by": input_data.triggered_by or "N/A",
            })
            return EscalationOutput(**result)
        except Exception as exc:
            logger.error("EscalationAgent failed: %s", exc)
            raise RuntimeError(f"EscalationAgent failed: {exc}") from exc
