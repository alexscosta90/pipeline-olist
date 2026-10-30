import shutil
from pathlib import Path

import pytest

from pipeline import db, marts


RAIZ = Path(__file__).resolve().parents[1]


def _preparar_refined(tmp_path, monkeypatch, pasta_marts):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "banco_teste.duckdb")
    monkeypatch.setattr(marts, "PASTA_MARTS", pasta_marts)
    monkeypatch.setattr(marts, "TABELAS_REFINED", ("pedidos", "itens_pedido"))
    con = db.conectar()
    try:
        db.criar_schema(con, "refined")
        con.execute(
            "CREATE TABLE refined.pedidos (pedido_id VARCHAR, cliente_id VARCHAR, "
            "status VARCHAR, data_compra TIMESTAMP, data_entrega_cliente TIMESTAMP, "
            "data_entrega_prevista DATE)"
        )
        con.execute(
            "CREATE TABLE refined.itens_pedido (pedido_id VARCHAR, preco DECIMAL(12,2))"
        )
        # Pedido válido com dois itens para testar soma e contagem distinta.
        # Pedido cancelado com item para testar exclusão de receita.
        # Entrega às 15h do próprio dia previsto para testar comparação por DATE.
        con.execute("""
            INSERT INTO refined.pedidos VALUES
            ('p1', 'c1', 'delivered', TIMESTAMP '2017-01-01 10:00:00',
             TIMESTAMP '2017-01-03 15:00:00', DATE '2017-01-03'),
            ('p2', 'c2', 'canceled', TIMESTAMP '2017-01-04 10:00:00',
             NULL, DATE '2017-01-08')
        """)
        con.execute("""
            INSERT INTO refined.itens_pedido VALUES
            ('p1', 10.00), ('p1', 5.00), ('p2', 99.00)
        """)
    finally:
        con.close()


def test_sql_01_e_03_agregam_pedido_e_entrega_no_dia_conta_no_prazo(tmp_path, monkeypatch):
    pasta = tmp_path / "sql"
    pasta.mkdir()
    for nome in ("01_vendas_mensais.sql", "03_entrega_no_prazo.sql"):
        shutil.copyfile(RAIZ / "sql" / "marts" / nome, pasta / nome)
    _preparar_refined(tmp_path, monkeypatch, pasta)

    marts.main()

    con = db.conectar()
    try:
        assert con.execute(
            "SELECT pedidos, receita FROM marts.vendas_mensais"
        ).fetchall() == [(1, 15.00)]
        assert con.execute(
            "SELECT entregues, no_prazo, atrasados, pct_no_prazo "
            "FROM marts.entrega_no_prazo"
        ).fetchall() == [(1, 1, 0, 100.0)]
    finally:
        con.close()


def test_arquivo_sem_prefixo_para_antes_de_executar_sql(tmp_path, monkeypatch):
    pasta = tmp_path / "sql"
    pasta.mkdir()
    (pasta / "sem_prefixo.sql").write_text("SELECT 1", encoding="utf-8")
    _preparar_refined(tmp_path, monkeypatch, pasta)

    with pytest.raises(SystemExit):
        marts.main()

    con = db.conectar()
    try:
        assert con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'marts'"
        ).fetchone() == (0,)
    finally:
        con.close()


def test_mart_vazio_encerra_e_preserva_schema_anterior(tmp_path, monkeypatch):
    pasta = tmp_path / "sql"
    pasta.mkdir()
    (pasta / "01_vazio.sql").write_text("SELECT 1 WHERE FALSE", encoding="utf-8")
    _preparar_refined(tmp_path, monkeypatch, pasta)
    con = db.conectar()
    try:
        db.criar_schema(con, "marts")
        con.execute("CREATE TABLE marts.antigo AS SELECT 42 AS valor")
    finally:
        con.close()

    with pytest.raises(SystemExit):
        marts.main()

    con = db.conectar()
    try:
        assert con.execute("SELECT valor FROM marts.antigo").fetchone() == (42,)
    finally:
        con.close()


def test_arquivo_removido_faz_mart_sumir_na_execucao_seguinte(tmp_path, monkeypatch):
    pasta = tmp_path / "sql"
    pasta.mkdir()
    arquivo = pasta / "01_presente.sql"
    arquivo.write_text("SELECT 7 AS valor", encoding="utf-8")
    (pasta / "02_outro.sql").write_text("SELECT 8 AS valor", encoding="utf-8")
    _preparar_refined(tmp_path, monkeypatch, pasta)
    marts.main()
    arquivo.unlink()

    marts.main()

    con = db.conectar()
    try:
        assert con.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'marts' AND table_name = 'presente'"
        ).fetchone() == (0,)
        assert con.execute("SELECT valor FROM marts.outro").fetchone() == (8,)
    finally:
        con.close()


def test_arquivos_e_nomes_rejeita_nomes_de_tabela_duplicados(tmp_path, monkeypatch):
    pasta = tmp_path / "sql"
    pasta.mkdir()
    (pasta / "01_metrica.sql").write_text("SELECT 1", encoding="utf-8")
    (pasta / "02_metrica.sql").write_text("SELECT 2", encoding="utf-8")
    monkeypatch.setattr(marts, "PASTA_MARTS", pasta)

    with pytest.raises(SystemExit):
        marts._arquivos_e_nomes()
