"""
Utilitários compartilhados para parsing de respostas estruturadas dos agentes ReAct.

Os agentes LLM são instruídos a incluir marcações no final de suas respostas
(ex: ESCALAR, FONTES, MOTIVO). Este módulo centraliza a extração via regex.
"""

import re

# Valores considerados como "vazio" ao extrair campos opcionais
_EMPTY_VALUES = ("N/A", "NA", "NONE", "")


def parse_escalar(raw: str) -> bool:
    """Extrai o campo ESCALAR: true/false de uma resposta."""
    match = re.search(r"ESCALAR:\s*(true|false)", raw, re.IGNORECASE)
    if match:
        return match.group(1).lower() == "true"
    return False


def parse_fontes(raw: str) -> list[str]:
    """Extrai o campo FONTES: [doc1.md, doc2.md] de uma resposta."""
    match = re.search(r"FONTES:\s*\[([^\]]+)\]", raw, re.IGNORECASE)
    if match:
        return [s.strip() for s in match.group(1).split(",") if s.strip()]
    return []


def parse_motivo(raw: str, field_name: str = "MOTIVO") -> str | None:
    """
    Extrai um campo de motivo/razão de uma resposta.

    Args:
        raw: texto completo da resposta do LLM
        field_name: nome do campo a extrair (ex: "MOTIVO", "MOTIVO_ESCALONAMENTO")

    Returns:
        O motivo extraído ou None se vazio/N/A.
    """
    pattern = rf"{field_name}:\s*(.+?)(?:\n|$)"
    match = re.search(pattern, raw, re.IGNORECASE)
    if match:
        motivo = match.group(1).strip()
        if motivo.upper() not in _EMPTY_VALUES:
            return motivo
    return None


def parse_nivel(raw: str) -> str | None:
    """Extrai o campo NIVEL: Risco | Financeiro | L2 | L1 | none de uma resposta."""
    match = re.search(
        r"NIVEL:\s*(Risco|Financeiro|L2|L1|none)", raw, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def parse_sql_usado(raw: str) -> str | None:
    """Extrai o campo SQL_USADO: <query> de uma resposta."""
    match = re.search(r"SQL_USADO:\s*(.+?)(?:\n\n|$)", raw, re.IGNORECASE | re.DOTALL)
    if match:
        sql_candidate = match.group(1).strip()
        if sql_candidate.upper() not in _EMPTY_VALUES:
            return sql_candidate
    return None
