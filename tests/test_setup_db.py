"""
Testes para setup_db.py — criação do banco SQLite a partir dos CSVs.
"""

import os
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect


def test_setup_creates_all_tables(tmp_path):
    """Verifica que setup() cria as três tabelas esperadas."""
    db_path = str(tmp_path / "test_setup.db")

    # Cria CSVs de teste
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    (data_dir / "clientes.csv").write_text(
        "cliente_id,nome_cliente,segmento\nC001,Loja Aurora,varejo\n",
        encoding="utf-8",
    )
    (data_dir / "pedidos.csv").write_text(
        "pedido_id,cliente_id,plano\nP1001,C001,Pro\n",
        encoding="utf-8",
    )
    (data_dir / "reembolsos.csv").write_text(
        "reembolso_id,pedido_id,status_reembolso\nR001,P1001,aprovado\n",
        encoding="utf-8",
    )

    with patch("core.config.DB_PATH", db_path):
        import importlib
        import setup_db as setup_module
        importlib.reload(setup_module)

        # Muda o diretório de trabalho para que os paths relativos dos CSVs funcionem
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            setup_module.setup()
        finally:
            os.chdir(original_cwd)

    # Verifica que o banco foi criado com as tabelas corretas
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "clientes" in tables
    assert "pedidos" in tables
    assert "reembolsos" in tables


def test_setup_populates_data(tmp_path):
    """Verifica que setup() insere os dados dos CSVs no banco."""
    db_path = str(tmp_path / "test_data.db")

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    (data_dir / "clientes.csv").write_text(
        "cliente_id,nome_cliente\nC001,Loja Aurora\nC002,Tech Store\n",
        encoding="utf-8",
    )
    (data_dir / "pedidos.csv").write_text(
        "pedido_id,cliente_id\nP1001,C001\n",
        encoding="utf-8",
    )
    (data_dir / "reembolsos.csv").write_text(
        "reembolso_id,pedido_id\nR001,P1001\nR002,P1001\n",
        encoding="utf-8",
    )

    with patch("core.config.DB_PATH", db_path):
        import importlib
        import setup_db as setup_module
        importlib.reload(setup_module)

        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            setup_module.setup()
        finally:
            os.chdir(original_cwd)

    # Verifica contagem de registros
    from sqlalchemy import text
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        clientes_count = conn.execute(text("SELECT COUNT(*) FROM clientes")).scalar()
        pedidos_count = conn.execute(text("SELECT COUNT(*) FROM pedidos")).scalar()
        reembolsos_count = conn.execute(text("SELECT COUNT(*) FROM reembolsos")).scalar()

    assert clientes_count == 2
    assert pedidos_count == 1
    assert reembolsos_count == 2


def test_setup_replaces_existing_data(tmp_path):
    """Verifica que setup() sobrescreve dados existentes (if_exists='replace')."""
    db_path = str(tmp_path / "test_replace.db")

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    (data_dir / "clientes.csv").write_text(
        "cliente_id,nome_cliente\nC001,Loja Aurora\n",
        encoding="utf-8",
    )
    (data_dir / "pedidos.csv").write_text(
        "pedido_id,cliente_id\nP1001,C001\n",
        encoding="utf-8",
    )
    (data_dir / "reembolsos.csv").write_text(
        "reembolso_id,pedido_id\nR001,P1001\n",
        encoding="utf-8",
    )

    with patch("core.config.DB_PATH", db_path):
        import importlib
        import setup_db as setup_module
        importlib.reload(setup_module)

        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            # Executa setup duas vezes — a segunda deve sobrescrever
            setup_module.setup()
            setup_module.setup()
        finally:
            os.chdir(original_cwd)

    from sqlalchemy import text
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM clientes")).scalar()

    # Não deve duplicar — replace garante apenas 1 registro
    assert count == 1
