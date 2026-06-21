"""
API REST do AtlasShop Assist — servidor FastAPI.

Uso:
    uvicorn api:app --reload
    uvicorn api:app --host 0.0.0.0 --port 8000

Endpoints principais:
    POST /chat                          → envia mensagem e recebe resposta
    GET  /session/{session_id}/history  → histórico da sessão
    DELETE /session/{session_id}        → encerra sessão e limpa histórico
    GET  /health                        → verifica se a API está no ar

Segurança:
    - Autenticação via header X-API-Key (variável API_KEY no .env)
    - CORS restritivo por padrão (apenas origens em CORS_ORIGINS no .env)
"""

# TODO: adicionar rate limiting por session_id ou user_id (ex: slowapi)
# TODO: adicionar logging estruturado (structlog ou loguru) com correlation_id por requisição
# TODO: substituir o dicionário _sessions por armazenamento persistente (Redis) em produção
# TODO: adicionar endpoint GET /sessions para listar sessões ativas (útil para monitoramento)

import logging
import os
import secrets

from fastapi import FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from orchestrator import Orchestrator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AtlasShop Assist API",
    description="Assistente conversacional interno para suporte e operações da AtlasShop.",
    version="0.1.0",
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None,
)


# ---------------------------------------------------------------------------
# CORS — restritivo por padrão
# ---------------------------------------------------------------------------

_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Autenticação — API Key via header X-API-Key
# ---------------------------------------------------------------------------

_API_KEY = os.getenv("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _verify_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    if not _API_KEY:
        return "anonymous"
    if not api_key or not secrets.compare_digest(api_key, _API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente.",
        )
    return api_key


# ---------------------------------------------------------------------------
# Armazenamento de sessões em memória
# Cada session_id mantém um Orchestrator próprio com histórico independente.
# ---------------------------------------------------------------------------

# TODO: substituir por Redis ou banco relacional para suportar múltiplos workers
_sessions: dict[str, Orchestrator] = {}


# ---------------------------------------------------------------------------
# Schemas de entrada e saída
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    # Mensagem enviada pelo atendente
    message: str = Field(..., min_length=1, max_length=4000, description="Mensagem do usuário")

    # Identifica a conversa — use um ID único por atendente ou ticket
    session_id: str = Field(default="default", description="ID da sessão (conversa)")

    # Identifica quem está usando o assistente
    user_id: str = Field(default="user", description="ID do usuário/atendente")

    # TODO: adicionar campo opcional `context` para o atendente passar info extra por mensagem


class ChatResponse(BaseModel):
    response: str
    session_id: str

    # TODO: adicionar campo `sources` extraído do KnowledgeAgent para rastreabilidade
    # TODO: adicionar campo `escalation` com nível e próximos passos quando houver escalonamento
    # TODO: adicionar campo `agent_used` indicando qual agente respondeu (knowledge/data/escalation)


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Envia uma mensagem ao assistente",
)
def chat(request: ChatRequest, _key: str = Security(_verify_api_key)):
    """
    Recebe uma mensagem do atendente, processa pelo orquestrador e retorna a resposta.

    O histórico da conversa é mantido automaticamente por session_id.
    Sessions novas são criadas automaticamente na primeira mensagem.
    """
    # TODO: validar se o user_id tem permissão para acessar a session_id informada
    # TODO: implementar timeout (ex: asyncio.wait_for) para evitar requisições presas
    # TODO: adicionar campo de erro estruturado na resposta em vez de HTTPException puro

    # Cria orquestrador da sessão se ainda não existir
    if request.session_id not in _sessions:
        # TODO: carregar histórico persistido do banco/Redis se a sessão já existiu antes
        _sessions[request.session_id] = Orchestrator()

    orchestrator = _sessions[request.session_id]

    try:
        response = orchestrator.chat(
            user_message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
        )
    except Exception as exc:
        # TODO: distinguir erros de API Groq (rate limit, timeout) de erros internos
        logger.exception("Erro ao processar mensagem na sessão %s", request.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar mensagem. Tente novamente.",
        )

    return ChatResponse(response=response, session_id=request.session_id)


@app.get(
    "/session/{session_id}/history",
    response_model=HistoryResponse,
    summary="Retorna o histórico de uma sessão",
)
def get_history(session_id: str, _key: str = Security(_verify_api_key)):
    """
    Retorna todas as mensagens trocadas em uma sessão.
    """
    # TODO: implementar paginação (parâmetros offset e limit)
    # TODO: se session_id não estiver em memória, buscar no armazenamento persistente

    if session_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão '{session_id}' não encontrada ou já encerrada.",
        )

    history = _sessions[session_id].chat_history

    return HistoryResponse(
        session_id=session_id,
        messages=history,
        total=len(history),
    )


@app.delete(
    "/session/{session_id}",
    summary="Encerra e limpa uma sessão",
)
def clear_session(session_id: str, _key: str = Security(_verify_api_key)):
    """
    Remove o histórico e o orquestrador da sessão da memória.
    """
    # TODO: também remover do armazenamento persistente (Redis/banco) se existir

    if session_id in _sessions:
        del _sessions[session_id]

    # Retorna 200 mesmo se a sessão não existia (idempotente)
    return {"message": f"Sessão '{session_id}' encerrada com sucesso."}


@app.get(
    "/health",
    summary="Verificação de saúde da API",
)
def health():
    """
    Endpoint simples para health check (load balancer, monitoramento).
    """
    # TODO: verificar conectividade com Groq (ping de modelo leve)
    # TODO: verificar se o banco SQLite está acessível
    # TODO: retornar versão da aplicação e timestamp

    return {"status": "ok"}
