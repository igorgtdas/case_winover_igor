"""
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
# Chave de API
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---------------------------------------------------------------------------
# Parâmetros por agente
# ---------------------------------------------------------------------------

# Guard Agent — filtro de segurança (deve ser rápido e determinístico)
GUARD_PARAMS = {
    "model":          os.getenv("GUARD_MODEL",          "llama-3.1-8b-instant"),
    "temperature":    float(os.getenv("GUARD_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("GUARD_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("GUARD_MAX_TOKENS",       "256")),
    "context_window": int(os.getenv("GUARD_CONTEXT_WINDOW",   "0")),  # stateless — não precisa de histórico
}

# Router Agent — classificador de intenção (deve ser rápido e determinístico)
ROUTER_PARAMS = {
    "model":          os.getenv("ROUTER_MODEL",          "llama-3.1-8b-instant"),
    "temperature":    float(os.getenv("ROUTER_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("ROUTER_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("ROUTER_MAX_TOKENS",       "256")),
    "context_window": int(os.getenv("ROUTER_CONTEXT_WINDOW",   "5")),
}

# Knowledge Agent — especialista em documentação (precisa de raciocínio robusto)
KNOWLEDGE_PARAMS = {
    "model":          os.getenv("KNOWLEDGE_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    float(os.getenv("KNOWLEDGE_TEMPERATURE",    "0.1")),
    "top_p":          float(os.getenv("KNOWLEDGE_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("KNOWLEDGE_MAX_TOKENS",       "1024")),
    "context_window": int(os.getenv("KNOWLEDGE_CONTEXT_WINDOW",   "5")),
}

# Data Agent — especialista em consultas SQL (deve ser preciso)
DATA_PARAMS = {
    "model":          os.getenv("DATA_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    float(os.getenv("DATA_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("DATA_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("DATA_MAX_TOKENS",       "1024")),
    "context_window": int(os.getenv("DATA_CONTEXT_WINDOW",   "5")),
}

# Escalation Agent — avalia escalonamento (precisa de raciocínio sobre regras complexas)
ESCALATION_PARAMS = {
    "model":          os.getenv("ESCALATION_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    float(os.getenv("ESCALATION_TEMPERATURE",    "0")),
    "top_p":          float(os.getenv("ESCALATION_TOP_P",          "1.0")),
    "max_tokens":     int(os.getenv("ESCALATION_MAX_TOKENS",       "512")),
    "context_window": int(os.getenv("ESCALATION_CONTEXT_WINDOW",   "0")),  # recebe contexto pronto do orquestrador
}

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
