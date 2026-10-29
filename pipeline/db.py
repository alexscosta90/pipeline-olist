"""Acesso ao banco da etapa raw.

PASTA_RAW aponta para os CSVs compactados distribuídos com o projeto, e o
arquivo DuckDB fica na raiz para que ingestão e exploração encontrem o mesmo
banco. gravar substitui a tabela para permitir reexecução segura e retorna a
contagem consultada no banco, que é a conferência da ingestão.
"""

from pathlib import Path

import pandas as pd


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ_PROJETO / "raw"
CAMINHO_BANCO = RAIZ_PROJETO / "olist.duckdb"


def conectar():
    """Abre o banco do projeto, criando-o se ainda não existir."""
    import duckdb

    return duckdb.connect(str(CAMINHO_BANCO))


def criar_schema(con, nome):
    """Garante a existência do schema solicitado."""
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{nome}"')


def gravar(con, df: pd.DataFrame, schema: str, tabela: str) -> int:
    """Substitui uma tabela pelo DataFrame e devolve sua contagem no banco."""
    relacao = "_df_ingestao_temporaria"
    con.register(relacao, df)
    try:
        con.execute(
            f'CREATE OR REPLACE TABLE "{schema}"."{tabela}" AS '
            f'SELECT * FROM "{relacao}"'
        )
    finally:
        con.unregister(relacao)

    return con.execute(
        f'SELECT COUNT(*) FROM "{schema}"."{tabela}"'
    ).fetchone()[0]
