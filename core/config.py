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

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


def _get_env_float(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        return float(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid value for %s=%r, falling back to %s", name, raw, default)
        return float(default)


def _get_env_int(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid value for %s=%r, falling back to %s", name, raw, default)
        return int(default)


# ---------------------------------------------------------------------------
# Chave de API
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning(
        "GROQ_API_KEY is not set. LLM calls will fail. "
        "Set it in .env or as an environment variable."
    )

# ---------------------------------------------------------------------------
# Parâmetros por agente
# ---------------------------------------------------------------------------

# Guard Agent — filtro de segurança (deve ser rápido e determinístico)
GUARD_PARAMS = {
    "model":          os.getenv("GUARD_MODEL",          "llama-3.1-8b-instant"),
    "temperature":    _get_env_float("GUARD_TEMPERATURE",    "0"),
    "top_p":          _get_env_float("GUARD_TOP_P",          "1.0"),
    "max_tokens":     _get_env_int("GUARD_MAX_TOKENS",       "256"),
    "context_window": _get_env_int("GUARD_CONTEXT_WINDOW",   "0"),
}

# Router Agent — classificador de intenção (deve ser rápido e determinístico)
ROUTER_PARAMS = {
    "model":          os.getenv("ROUTER_MODEL",          "llama-3.1-8b-instant"),
    "temperature":    _get_env_float("ROUTER_TEMPERATURE",    "0"),
    "top_p":          _get_env_float("ROUTER_TOP_P",          "1.0"),
    "max_tokens":     _get_env_int("ROUTER_MAX_TOKENS",       "256"),
    "context_window": _get_env_int("ROUTER_CONTEXT_WINDOW",   "5"),
}

# Knowledge Agent — especialista em documentação (precisa de raciocínio robusto)
KNOWLEDGE_PARAMS = {
    "model":          os.getenv("KNOWLEDGE_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    _get_env_float("KNOWLEDGE_TEMPERATURE",    "0.1"),
    "top_p":          _get_env_float("KNOWLEDGE_TOP_P",          "1.0"),
    "max_tokens":     _get_env_int("KNOWLEDGE_MAX_TOKENS",       "1024"),
    "context_window": _get_env_int("KNOWLEDGE_CONTEXT_WINDOW",   "5"),
}

# Data Agent — especialista em consultas SQL (deve ser preciso)
DATA_PARAMS = {
    "model":          os.getenv("DATA_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    _get_env_float("DATA_TEMPERATURE",    "0"),
    "top_p":          _get_env_float("DATA_TOP_P",          "1.0"),
    "max_tokens":     _get_env_int("DATA_MAX_TOKENS",       "1024"),
    "context_window": _get_env_int("DATA_CONTEXT_WINDOW",   "5"),
}

# Escalation Agent — avalia escalonamento (precisa de raciocínio sobre regras complexas)
ESCALATION_PARAMS = {
    "model":          os.getenv("ESCALATION_MODEL",          "llama-3.3-70b-versatile"),
    "temperature":    _get_env_float("ESCALATION_TEMPERATURE",    "0"),
    "top_p":          _get_env_float("ESCALATION_TOP_P",          "1.0"),
    "max_tokens":     _get_env_int("ESCALATION_MAX_TOKENS",       "512"),
    "context_window": _get_env_int("ESCALATION_CONTEXT_WINDOW",   "0"),
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
