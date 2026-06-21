"""
Executa uma vez para criar o banco SQLite a partir dos CSVs.
Uso: python setup_db.py
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from core.config import DB_PATH


def setup():
    tables = {
        "clientes":   "data/clientes.csv",
        "pedidos":    "data/pedidos.csv",
        "reembolsos": "data/reembolsos.csv",
    }

    missing = [p for p in tables.values() if not Path(p).is_file()]
    if missing:
        print(f"[ERRO] Arquivos CSV não encontrados: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
    except Exception as exc:
        print(f"[ERRO] Falha ao criar engine do banco de dados: {exc}", file=sys.stderr)
        sys.exit(1)

    for table_name, csv_path in tables.items():
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            print(f"[ERRO] Falha ao ler '{csv_path}': {exc}", file=sys.stderr)
            sys.exit(1)

        try:
            df.to_sql(table_name, engine, if_exists="replace", index=False)
        except Exception as exc:
            print(f"[ERRO] Falha ao criar tabela '{table_name}': {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"Tabela '{table_name}' criada com {len(df)} registros")

    print(f"\nBanco disponível em: {DB_PATH}")


if __name__ == "__main__":
    setup()
