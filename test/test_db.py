import pandas as pd

from pipeline import db


def test_gravar_substitui_tabela_e_retorna_contagem(tmp_path, monkeypatch):
    # Três linhas pequenas inventadas para conferir criação e substituição.
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "unitario.duckdb")
    con = db.conectar()
    try:
        db.criar_schema(con, "raw")
        primeira = pd.DataFrame({"codigo": ["A", "B"]})
        assert db.gravar(con, primeira, "raw", "amostra") == 2

        segunda = pd.DataFrame({"codigo": ["C"]})
        assert db.gravar(con, segunda, "raw", "amostra") == 1
        assert con.execute("SELECT codigo FROM raw.amostra").fetchall() == [("C",)]
        assert con.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = 'raw'"
        ).fetchone() == ("raw",)
    finally:
        con.close()
