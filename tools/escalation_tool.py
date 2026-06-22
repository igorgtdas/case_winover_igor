"""
tools/escalation_tool.py — Tool de Registro de Escalonamentos

Registra escalonamentos no banco SQLite (tabela escalation_logs).
Chamada pelo Orchestrator após o EscalationAgent confirmar should_escalate=True.

Cria a tabela automaticamente se não existir e executa migrações
não-destrutivas para bancos criados em versões anteriores.
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


def log_escalation(
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
    """Registra um escalonamento na tabela escalation_logs do banco SQLite."""
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text(_CREATE_TABLE))

            for stmt in _MIGRATE_COLUMNS:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass  # coluna já existe

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
        logger.error("Falha ao registrar escalonamento: %s", exc)
