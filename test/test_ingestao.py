import gzip

import pytest

from pipeline import db, ingestao


def test_csv_inventado_vira_tabela_com_as_mesmas_linhas(tmp_path, monkeypatch):
    pasta = tmp_path / "raw"
    pasta.mkdir()
    # Dois registros inventados; o zero à esquerda testa preservação de texto.
    with gzip.open(pasta / "amostra.csv.gz", "wt", encoding="utf-8", newline="") as arquivo:
        arquivo.write("id,valor\n001,10\n002,20\n")
    monkeypatch.setattr(ingestao, "PASTA_RAW", pasta)
    monkeypatch.setattr(ingestao, "ARQUIVOS_TABELAS", (("amostra.csv.gz", "amostra"),))
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "ingestao.duckdb")

    ingestao.main()

    con = db.conectar()
    try:
        assert con.execute("SELECT * FROM raw.amostra ORDER BY id").fetchall() == [
            ("001", "10"), ("002", "20")
        ]
    finally:
        con.close()


def test_arquivo_ausente_encerra_antes_de_criar_banco(tmp_path, monkeypatch):
    pasta = tmp_path / "raw"
    pasta.mkdir()
    caminho_banco = tmp_path / "nao_criar.duckdb"
    monkeypatch.setattr(ingestao, "PASTA_RAW", pasta)
    monkeypatch.setattr(ingestao, "ARQUIVOS_TABELAS", (("ausente.csv.gz", "amostra"),))
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco)

    with pytest.raises(SystemExit):
        ingestao.main()
    assert not caminho_banco.exists()
