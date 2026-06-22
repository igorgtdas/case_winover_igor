"""
================================================================================
core/rate_limit.py — Tratamento de Rate Limit da API Groq
================================================================================

O QUE É:
    Módulo utilitário que re-exporta RateLimitError do SDK Groq e define a
    mensagem amigável exibida ao usuário quando o limite de requisições é atingido.

PARA QUE SERVE:
    - Centralizar a captura de erros de rate limit em um único ponto
    - Evitar que o Orchestrator propague um HTTP 500 ao usuário quando a API
      Groq retorna 429 (Too Many Requests)
    - Fornecer mensagem em português orientando o colaborador a aguardar

O QUE USA:
    - groq.RateLimitError → importado diretamente do SDK oficial da Groq

COM QUEM CONVERSA:
    ← Nenhum (módulo folha)
    → Importado por: orchestrator.py, que envolve o bloco de agentes em
       try/except RateLimitError e retorna MENSAGEM_RATE_LIMIT ao usuário

================================================================================
Tratamento de rate limit do Groq.

Expõe RateLimitError para que o orchestrator possa capturar
e retornar uma mensagem amigável ao usuário sem propagar o 500.
"""

from groq import RateLimitError  # re-exportado para uso no orchestrator

MENSAGEM_RATE_LIMIT = (
    "O assistente está temporariamente sobrecarregado (limite de requisições atingido). "
    "Aguarde alguns instantes e tente novamente."
)

__all__ = ["RateLimitError", "MENSAGEM_RATE_LIMIT"]
