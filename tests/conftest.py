"""
Fixtures compartilhadas para os testes do AtlasShop Assist.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import pandas as pd
from sqlalchemy import create_engine

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def mock_groq_api_key(monkeypatch):
    """Injeta uma API key falsa para evitar erros de configuração."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-tests")


@pytest.fixture
def tmp_db(tmp_path):
    """Cria um banco SQLite temporário com dados de teste."""
    db_path = str(tmp_path / "test.db")
    engine = create_engine(f"sqlite:///{db_path}")

    clientes_data = {
        "cliente_id": ["C001", "C002", "C003"],
        "nome_cliente": ["Loja Aurora", "Tech Store", "Fashion Hub"],
        "segmento": ["varejo", "tech", "moda"],
        "plano": ["Pro", "Enterprise", "Essencial"],
        "cidade": ["São Paulo", "Rio de Janeiro", "Curitiba"],
        "estado": ["SP", "RJ", "PR"],
        "mrr_brl": [500.0, 1200.0, 200.0],
        "status_cliente": ["ativo", "ativo", "churned"],
        "data_inicio": ["2024-01-15", "2023-06-01", "2024-03-10"],
        "owner_cs": ["Ana", "Carlos", "Maria"],
    }

    pedidos_data = {
        "pedido_id": ["P1001", "P1002", "P1003"],
        "cliente_id": ["C001", "C002", "C003"],
        "plano": ["Pro", "Enterprise", "Essencial"],
        "ciclo": ["mensal", "anual", "mensal"],
        "valor_brl": [500.0, 14400.0, 200.0],
        "status_pedido": ["ativo", "ativo", "cancelado"],
        "status_pagamento": ["pago", "fraud_review", "reembolsado"],
        "data_ativacao": ["2024-01-15", "2023-06-01", "2024-03-10"],
        "data_cancelamento": [None, None, "2024-06-15"],
        "ultimo_evento_em": ["2024-05-01", "2024-05-10", "2024-06-15"],
        "canal_origem": ["site", "indicacao", "site"],
        "observacao_operacional": [None, "Em análise de fraude", "Cliente solicitou cancelamento"],
    }

    reembolsos_data = {
        "reembolso_id": ["R001", "R002"],
        "pedido_id": ["P1003", "P1003"],
        "status_reembolso": ["aprovado", "pendente"],
        "motivo": ["cancelamento", "cobrança duplicada"],
        "valor_brl": [200.0, 200.0],
        "criado_em": ["2024-06-16", "2024-06-20"],
        "atualizado_em": ["2024-06-17", "2024-06-20"],
        "observacao": ["Reembolso processado", None],
    }

    pd.DataFrame(clientes_data).to_sql("clientes", engine, if_exists="replace", index=False)
    pd.DataFrame(pedidos_data).to_sql("pedidos", engine, if_exists="replace", index=False)
    pd.DataFrame(reembolsos_data).to_sql("reembolsos", engine, if_exists="replace", index=False)

    return db_path


@pytest.fixture
def tmp_knowledge_dir(tmp_path):
    """Cria um diretório de knowledge temporário com documentos de teste."""
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    (knowledge_dir / "faq_atendimento.md").write_text(
        "# FAQ Atendimento\n\n## Horário de atendimento\nSegunda a sexta, 9h às 18h.",
        encoding="utf-8",
    )
    (knowledge_dir / "politica_cancelamento.md").write_text(
        "# Política de Cancelamento\n\nO cliente pode cancelar em até 7 dias.",
        encoding="utf-8",
    )

    return str(knowledge_dir)
