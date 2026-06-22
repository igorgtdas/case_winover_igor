"""
================================================================================
core/config.py — Configurações Centrais e Factory de LLM
================================================================================

O QUE É:
    Módulo de configuração central. Define os parâmetros de cada agente e expõe
    a função build_llm() usada por todos os agentes para instanciar seu modelo.

PARA QUE SERVE:
    - Carregar variáveis do .env (chaves de API, parâmetros de modelo, paths)
    - Permitir troca de modelo/provider por agente sem alterar o código dos agentes
    - Suportar dois providers: Groq (padrão) e OpenAI (via variável AGENT_PROVIDER)

O QUE USA:
    - python-dotenv → lê o arquivo .env
    - langchain_groq.ChatGroq e langchain_openai.ChatOpenAI (importados sob demanda)
    - Variáveis de ambiente com prefixo por agente: GUARD_*, ROUTER_*, KNOWLEDGE_*,
      DATA_*, ESCALATION_*

COM QUEM CONVERSA:
    ← Nenhum (módulo folha — não importa outros módulos do projeto)
    → Usado por: todos os agentes (guard, router, knowledge, data, escalation)
       e indiretamente por core/database.py e core/knowledge_loader.py

================================================================================
Configurações centrais do AtlasShop Assist.

Todas as variáveis são carregadas do .env (ou do ambiente).
Cada agente tem seu bloco independente de parâmetros — altere sem mexer no código dos agentes.

Parâmetros disponíveis por agente:
    model           → ID do modelo Groq
    temperature     → criatividade (0 = determinístico, 1 = mais criativo)
    top_p           → nucleus sampling (1.0 = desativado)
    max_tokens      → limite de tokens na resposta do modelo
    context_window  → quantas mensagens anteriores o agente recebe (0 = sem memória)
                      cada "turno" conta como 2 mensagens (user + assistant)
                      ex: context_window=5 → últimas 5 perguntas + 5 respostas
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Chaves de API
# ---------------------------------------------------------------------------

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---------------------------------------------------------------------------
# Parâmetros por agente
# ---------------------------------------------------------------------------

# Guard Agent — filtro de segurança (deve ser rápido e determinístico)
GUARD_PARAMS = {
    "provider":       os.getenv("GUARD_PROVIDER",       "groq"),
    "model":          os.getenv("GUARD_MODEL",          "llama-3.1-8b-instant"),
    "temperature":    float(os.getenv("GUARD_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("GUARD_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("GUARD_MAX_TOKENS",       "256")),
    "context_window": int(os.getenv("GUARD_CONTEXT_WINDOW",   "0")),
}

# Router Agent — classificador de intenção (deve ser rápido e determinístico)
ROUTER_PARAMS = {
    "provider":       os.getenv("ROUTER_PROVIDER",       "groq"),
    "model":          os.getenv("ROUTER_MODEL",          "llama-3.1-8b-instant"),
    "temperature":    float(os.getenv("ROUTER_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("ROUTER_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("ROUTER_MAX_TOKENS",       "256")),
    "context_window": int(os.getenv("ROUTER_CONTEXT_WINDOW",   "5")),
}

# Knowledge Agent — especialista em documentação (precisa de raciocínio robusto)
KNOWLEDGE_PARAMS = {
    "provider":       os.getenv("KNOWLEDGE_PROVIDER",       "groq"),
    "model":          os.getenv("KNOWLEDGE_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    float(os.getenv("KNOWLEDGE_TEMPERATURE",    "0.1")),
    "top_p":          float(os.getenv("KNOWLEDGE_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("KNOWLEDGE_MAX_TOKENS",       "1024")),
    "context_window": int(os.getenv("KNOWLEDGE_CONTEXT_WINDOW",   "5")),
}

# Data Agent — especialista em consultas SQL (deve ser preciso)
DATA_PARAMS = {
    "provider":       os.getenv("DATA_PROVIDER",       "groq"),
    "model":          os.getenv("DATA_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    float(os.getenv("DATA_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("DATA_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("DATA_MAX_TOKENS",       "1024")),
    "context_window": int(os.getenv("DATA_CONTEXT_WINDOW",   "5")),
}

# Escalation Agent — avalia escalonamento (precisa de raciocínio sobre regras complexas)
ESCALATION_PARAMS = {
    "provider":       os.getenv("ESCALATION_PROVIDER",       "groq"),
    "model":          os.getenv("ESCALATION_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    float(os.getenv("ESCALATION_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("ESCALATION_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("ESCALATION_MAX_TOKENS",       "512")),
    "context_window": int(os.getenv("ESCALATION_CONTEXT_WINDOW",   "0")),
}

# ---------------------------------------------------------------------------
# Factory de LLM — instancia Groq ou OpenAI conforme o provider do agente
# ---------------------------------------------------------------------------

def build_llm(params: dict):
    """
    Retorna um ChatLLM configurado com base nos params do agente.
    Provider é lido do campo 'provider': 'groq' (padrão) ou 'openai'.

    Uso nos agentes:
        from core.config import build_llm, KNOWLEDGE_PARAMS
        llm = build_llm(KNOWLEDGE_PARAMS)
    """
    provider    = params.get("provider", "groq").lower()
    model       = params["model"]
    temperature = params["temperature"]
    max_tokens  = params["max_tokens"]
    top_p       = params["top_p"]

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            api_key=OPENAI_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={"top_p": top_p},
        )

    # padrão: groq
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model,
        api_key=GROQ_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
        model_kwargs={"top_p": top_p},
    )


# ---------------------------------------------------------------------------
# Atalho legado (mantido para não quebrar imports existentes)
# ---------------------------------------------------------------------------

MODELS = {
    "guard":      GUARD_PARAMS["model"],
    "router":     ROUTER_PARAMS["model"],
    "knowledge":  KNOWLEDGE_PARAMS["model"],
    "data":       DATA_PARAMS["model"],
    "escalation": ESCALATION_PARAMS["model"],
}

# ---------------------------------------------------------------------------
# Infraestrutura
# ---------------------------------------------------------------------------

DB_PATH       = os.getenv("DB_PATH",       "atlasshop.db")
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")
