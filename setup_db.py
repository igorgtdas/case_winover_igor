"""
Executa uma vez para criar o banco SQLite a partir dos CSVs.
Uso: python setup_db.py
"""

import pandas as pd
from sqlalchemy import create_engine
from core.config import DB_PATH


def setup():
    engine = create_engine(f"sqlite:///{DB_PATH}")

    tables = {
        "clientes":   "data/clientes.csv",
        "pedidos":    "data/pedidos.csv",
        "reembolsos": "data/reembolsos.csv",
    }

    for table_name, csv_path in tables.items():
        df = pd.read_csv(csv_path)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"Tabela '{table_name}' criada com {len(df)} registros")

    print(f"\nBanco disponível em: {DB_PATH}")


if __name__ == "__main__":
    setup()
