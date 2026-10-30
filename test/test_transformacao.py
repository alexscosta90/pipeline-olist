import pytest
from decimal import Decimal

from pipeline import db, transformacao


def _preparar_banco_temporario(tmp_path, monkeypatch, linhas):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "transformacao.duckdb")
    monkeypatch.setattr(
        transformacao,
        "COLUNAS",
        {"pedidos": [
            ("order_id", "pedido_id", "VARCHAR"),
            ("order_purchase_timestamp", "data_compra", "TIMESTAMP"),
            ("order_estimated_delivery_date", "data_prevista", "DATE"),
            ("price", "preco", "DECIMAL(12,2)"),
        ]},
    )
    monkeypatch.setattr(transformacao, "CHAVES", {"pedidos": ("pedido_id",)})
    con = db.conectar()
    try:
        db.criar_schema(con, "raw")
        con.execute(
            "CREATE TABLE raw.pedidos(order_id VARCHAR, "
            "order_purchase_timestamp VARCHAR, order_estimated_delivery_date VARCHAR, "
            "price VARCHAR)"
        )
        con.executemany("INSERT INTO raw.pedidos VALUES (?, ?, ?, ?)", linhas)
    finally:
        con.close()


def test_duplicata_exata_e_removida_e_tipos_convertidos(tmp_path, monkeypatch):
    # Repetição idêntica para provar DISTINCT; um segundo pedido para conferir duas linhas.
    _preparar_banco_temporario(tmp_path, monkeypatch, [
        ("p1", "2017-01-02 15:30:00", "2017-01-10", "12.40"),
        ("p1", "2017-01-02 15:30:00", "2017-01-10", "12.40"),
        ("p2", "2017-02-03 10:00:00", "2017-02-12", "7.00"),
    ])

    transformacao.main()

    con = db.conectar()
    try:
        assert con.execute("SELECT count(*) FROM refined.pedidos").fetchone() == (2,)
        assert con.execute(
            "SELECT typeof(data_compra), typeof(preco) FROM refined.pedidos LIMIT 1"
        ).fetchone() == ("TIMESTAMP", "DECIMAL(12,2)")
        assert con.execute(
            "SELECT typeof(data_prevista) FROM refined.pedidos LIMIT 1"
        ).fetchone() == ("DATE",)
        assert con.execute(
            "SELECT preco FROM refined.pedidos WHERE pedido_id = 'p1'"
        ).fetchone() == (Decimal("12.40"),)
    finally:
        con.close()


def test_data_invalida_encerra_sem_gravar_tabela_refined(tmp_path, monkeypatch):
    # Data inválida inventada força a validação estrita de conversão.
    _preparar_banco_temporario(tmp_path, monkeypatch, [
        ("p1", "ontem", "2017-01-10", "12.40"),
    ])

    with pytest.raises(SystemExit):
        transformacao.main()

    con = db.conectar()
    try:
        assert con.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'refined' AND table_name = 'pedidos'"
        ).fetchone() == (0,)
    finally:
        con.close()


def test_chave_repetida_com_conteudo_diferente_encerra(tmp_path, monkeypatch):
    # Mesmo pedido com datas distintas é um conflito, não uma duplicata exata.
    _preparar_banco_temporario(tmp_path, monkeypatch, [
        ("p1", "2017-01-02 15:30:00", "2017-01-10", "12.40"),
        ("p1", "2017-01-03 15:30:00", "2017-01-10", "12.40"),
    ])

    with pytest.raises(SystemExit):
        transformacao.main()

    con = db.conectar()
    try:
        assert con.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'refined' AND table_name = 'pedidos'"
        ).fetchone() == (0,)
    finally:
        con.close()


def test_pagamento_sem_valor_nao_e_gravado(tmp_path, monkeypatch):
    # Um pagamento com valor e um registro sem valor para validar o filtro documentado.
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "pagamentos_teste.duckdb")
    monkeypatch.setattr(transformacao, "COLUNAS", {
        "pagamentos": [
            ("order_id", "pedido_id", "VARCHAR"),
            ("payment_sequential", "pagamento_seq", "INTEGER"),
            ("payment_value", "valor", "DECIMAL(12,2)"),
        ]
    })
    monkeypatch.setattr(transformacao, "CHAVES", {"pagamentos": ("pedido_id", "pagamento_seq")})
    con = db.conectar()
    try:
        db.criar_schema(con, "raw")
        con.execute("CREATE TABLE raw.pagamentos(order_id VARCHAR, payment_sequential VARCHAR, payment_value VARCHAR)")
        con.execute("INSERT INTO raw.pagamentos VALUES ('p1', '1', '5.00'), ('p2', '1', NULL)")
    finally:
        con.close()

    transformacao.main()

    con = db.conectar()
    try:
        assert con.execute("SELECT pedido_id, valor FROM refined.pagamentos").fetchall() == [
            ("p1", Decimal("5.00"))
        ]
    finally:
        con.close()
