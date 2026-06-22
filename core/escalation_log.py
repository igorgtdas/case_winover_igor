"""
================================================================================
core/escalation_log.py — Registro de Escalonamentos no Banco de Dados
================================================================================

O QUE É:
    Módulo de persistência responsável por gravar cada escalonamento gerado
    pelo EscalationAgent na tabela `escalation_logs` do SQLite.

PARA QUE SERVE:
    - Criar a tabela automaticamente se não existir (self-migrating)
    - Executar migrações não-destrutivas quando novas colunas são adicionadas
      (ex: pedido_id, tipo) sem precisar recriar o banco
    - Registrar: quem escalou, qual sessão, qual nível (L1/L2/Financeiro/Risco),
      motivo, evidência, próximos passos, mensagem original e colaborador responsável

O QUE USA:
    - SQLAlchemy (text + engine) → executa INSERT no banco SQLite
    - core/database.py → get_engine() para obter a conexão
    - datetime/timezone → timestamp ISO 8601 em UTC

COM QUEM CONVERSA:
    ← Chamado por: orchestrator.py nos três pontos de escalonamento:
        1. GuardAgent detecta should_escalate=True (categoria: Risco)
        2. GuardAgent bloqueia por security (injection/jailbreak)
        3. RouterAgent encaminha para escalation e EscalationAgent confirma
    → Persiste em: atlasshop.db (tabela escalation_logs)

================================================================================
Registro de escalonamentos no banco de dados.

Cria a tabela `escalation_logs` automaticamente na primeira chamada (se não existir).
Cada escalonamento gera uma linha com todas as informações relevantes para auditoria.

Schema da tabela:
    id               INTEGER  PRIMARY KEY AUTOINCREMENT
    created_at       TEXT     timestamp ISO 8601
    session_id       TEXT
    user_id          TEXT
    user_name        TEXT     (do SessionContext, se disponível)
    user_email       TEXT     (do SessionContext, se disponível)
    plano            TEXT     (do SessionContext, se disponível)
    nivel            TEXT     L1 | L2 | Financeiro | Risco | none
    motivo           TEXT
    evidencia        TEXT
    proximos_passos  TEXT
    mensagem_usuario TEXT     mensagem original que disparou o escalonamento
    triggered_by     TEXT     knowledge_agent | data_agent | user
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import text
from core.database import get_engine

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS escalation_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT    NOT NULL,
    session_id       TEXT,
    user_id          TEXT,
    user_name        TEXT,
    user_email       TEXT,
    plano            TEXT,
    nivel            TEXT,
    motivo           TEXT,
    evidencia        TEXT,
    proximos_passos  TEXT,
    mensagem_usuario TEXT,
    triggered_by     TEXT,
    pedido_id        TEXT,
    tipo             TEXT
)
"""

_MIGRATE_COLUMNS = [
    "ALTER TABLE escalation_logs ADD COLUMN pedido_id TEXT",
    "ALTER TABLE escalation_logs ADD COLUMN tipo TEXT",
]


def registrar_escalamento(
    session_id: str,
    user_id: str,
    mensagem_usuario: str,
    nivel: str,
    motivo: str,
    evidencia: str,
    proximos_passos: str,
    triggered_by: str,
    user_name: str | None = None,
    user_email: str | None = None,
    plano: str | None = None,
    pedido_id: str | None = None,
    tipo: str | None = None,
) -> None:
    """
    Insere um registro de escalonamento na tabela escalation_logs.
    Cria a tabela automaticamente se ainda não existir.
    """
    engine = get_engine()
    try:
        with engine.begin() as conn:
            # Garante que a tabela existe
            conn.execute(text(_CREATE_TABLE))

            # Migração não-destrutiva: adiciona colunas novas se o banco já existia
            for stmt in _MIGRATE_COLUMNS:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass  # coluna já existe — ignorar

            conn.execute(
                text("""
                    INSERT INTO escalation_logs (
                        created_at, session_id, user_id,
                        user_name, user_email, plano,
                        nivel, motivo, evidencia,
                        proximos_passos, mensagem_usuario, triggered_by,
                        pedido_id, tipo
                    ) VALUES (
                        :created_at, :session_id, :user_id,
                        :user_name, :user_email, :plano,
                        :nivel, :motivo, :evidencia,
                        :proximos_passos, :mensagem_usuario, :triggered_by,
                        :pedido_id, :tipo
                    )
                """),
                {
                    "created_at":       datetime.now(timezone.utc).isoformat(),
                    "session_id":       session_id,
                    "user_id":          user_id,
                    "user_name":        user_name,
                    "user_email":       user_email,
                    "plano":            plano,
                    "nivel":            nivel,
                    "motivo":           motivo,
                    "evidencia":        evidencia,
                    "proximos_passos":  proximos_passos,
                    "mensagem_usuario": mensagem_usuario,
                    "triggered_by":     triggered_by,
                    "pedido_id":        pedido_id,
                    "tipo":             tipo,
                },
            )
        logger.info(
            "Escalonamento registrado — session=%s nivel=%s triggered_by=%s",
            session_id, nivel, triggered_by,
        )
    except Exception as exc:
        # Log do erro mas não interrompe o fluxo — o usuário já recebeu a resposta padrão
        logger.error("Falha ao registrar escalonamento no banco: %s", exc)
