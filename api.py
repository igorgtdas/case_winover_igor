"""
================================================================================
api.py — API REST do AtlasShop Assist (FastAPI)
================================================================================

O QUE É:
    Ponto de entrada do sistema. Servidor HTTP que expõe os endpoints REST para
    consumo pelo frontend (chat interface, Flowise, Postman, etc.).

PARA QUE SERVE:
    Receber mensagens dos atendentes via HTTP e coordenar o ciclo de vida das
    sessões. Cada session_id mantém um Orchestrator próprio com histórico
    independente em memória.

    Endpoints:
      POST   /session/start              → cria sessão com contexto do colaborador
      POST   /chat                       → envia mensagem, recebe resposta do assistente
      GET    /session/{id}/history       → retorna histórico completo da sessão
      DELETE /session/{id}               → encerra sessão e libera memória
      GET    /health                     → health check (status + nº de sessões ativas)

O QUE USA:
    - FastAPI → framework HTTP com validação automática via Pydantic
    - orchestrator.py → Orchestrator (instanciado por sessão, guarda chat_history)
    - core/session_context.py → SessionContext (criado via /session/start)
    - Armazenamento em memória (_sessions, _contextos) — sem banco de dados para sessões

COM QUEM CONVERSA:
    ← Chamado por: cliente HTTP externo (Postman, frontend, Flowise)
    → Chama: Orchestrator.chat() para cada POST /chat
    → Não acessa banco, agentes ou LLM diretamente — tudo passa pelo Orchestrator

================================================================================
API REST do AtlasShop Assist — servidor FastAPI.

Uso:
    uvicorn api:app --reload
    uvicorn api:app --host 0.0.0.0 --port 8000

Endpoints principais:
    POST /chat                          → envia mensagem e recebe resposta
    GET  /session/{session_id}/history  → histórico da sessão
    DELETE /session/{session_id}        → encerra sessão e limpa histórico
    GET  /health                        → verifica se a API está no ar
"""


from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from orchestrator import Orchestrator
from core.session_context import SessionContext


# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AtlasShop Assist API",
    description="Assistente conversacional interno para suporte e operações da AtlasShop.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Armazenamento de sessões em memória
# Cada session_id mantém um Orchestrator próprio com histórico independente.
# ---------------------------------------------------------------------------

_sessions: dict[str, Orchestrator] = {}

# Contexto inicial de cada sessão (preenchido via POST /session/start)
_contextos: dict[str, SessionContext] = {}


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


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_selected: str


class SessionStartRequest(BaseModel):
    """Variáveis de entrada coletadas antes da primeira mensagem — equivalente ao Start Node do Flowise."""

    session_id: str = Field(..., description="ID único da sessão a ser iniciada")
    user_name: str = Field(..., description="Nome do atendente")
    user_email: str = Field(..., description="Email do atendente")



class SessionStartResponse(BaseModel):
    session_id: str
    message: str
    contexto: dict   # devolve o contexto criado para confirmação


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]
    total: int
    contexto: dict | None = None
    system_prompt_preview: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/session/start",
    response_model=SessionStartResponse,
    summary="Inicia uma sessão com contexto inicial (Start State)",
)
def session_start(request: SessionStartRequest):
    """
    Cria uma sessão nova com as variáveis de contexto preenchidas.
    Deve ser chamado UMA VEZ antes de enviar a primeira mensagem via POST /chat.

    As variáveis (user_name, user_email, plano) são armazenadas e injetadas
    automaticamente no prompt de cada agente durante toda a conversa.

    Exemplo de uso pelo terminal:
        curl -s -X POST http://localhost:8000/session/start \\
          -H "Content-Type: application/json" \\
          -d '{
            "session_id": "sessao-01",
            "user_name": "João Silva",
            "user_email": "joao@atlasshop.com",
          }'
    """

    # Cria o contexto e armazena
    try:
        contexto = SessionContext(
            user_name=request.user_name,
            user_email=request.user_email,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Contexto inválido: {str(exc)}",
        )

    # Cria o Orchestrator da sessão junto com o contexto
    _contextos[request.session_id] = contexto
    _sessions[request.session_id] = Orchestrator()

    return SessionStartResponse(
        session_id=request.session_id,
        message=f"Sessão '{request.session_id}' iniciada com sucesso.",
        contexto=contexto.model_dump(),
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Envia uma mensagem ao assistente",
)
def chat(request: ChatRequest):
    """
    Recebe uma mensagem do atendente, processa pelo orquestrador e retorna a resposta.

    O histórico da conversa é mantido automaticamente por session_id.
    Sessions novas são criadas automaticamente na primeira mensagem.
    """

    # Cria orquestrador da sessão se ainda não existir
    # (permite usar /chat sem /session/start — contexto fica None)
    if request.session_id not in _sessions:
        _sessions[request.session_id] = Orchestrator()

    orchestrator = _sessions[request.session_id]

    # Recupera contexto da sessão (None se /session/start não foi chamado)
    contexto = _contextos.get(request.session_id)

    try:
        response, agent_selected = orchestrator.chat(
            user_message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            session_context=contexto,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar mensagem: {str(exc)}",
        )

    return ChatResponse(response=response, session_id=request.session_id, agent_selected=agent_selected)


@app.get(
    "/session/{session_id}/history",
    response_model=HistoryResponse,
    summary="Retorna o histórico de uma sessão",
)
def get_history(session_id: str):
    """
    Retorna todas as mensagens trocadas em uma sessão.
    """

    if session_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão '{session_id}' não encontrada ou já encerrada.",
        )

    history = _sessions[session_id].chat_history
    contexto = _contextos.get(session_id)

    return HistoryResponse(
        session_id=session_id,
        messages=history,
        total=len(history),
        contexto=contexto.model_dump() if contexto else None,
        system_prompt_preview=_sessions[session_id].system_prompt_preview,
    )


@app.delete(
    "/session/{session_id}",
    summary="Encerra e limpa uma sessão",
)
def clear_session(session_id: str):
    """
    Remove o histórico e o orquestrador da sessão da memória.
    """

    if session_id in _sessions:
        del _sessions[session_id]
    if session_id in _contextos:
        del _contextos[session_id]

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

    return {
        "status": "ok",
        "sessions_ativas": len(_sessions),
    }
