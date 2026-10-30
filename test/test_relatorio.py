import re

import duckdb

import relatorio


def _criar_marts_inventados(caminho):
    con = duckdb.connect(str(caminho))
    try:
        con.execute("CREATE SCHEMA marts")
        # Valores inventados para conferir formatação dos sete cartões.
        con.execute("""
            CREATE TABLE marts.kpis AS SELECT
                25.5 AS ticket_medio, 1.25 AS pct_cancelados,
                14.2 AS pct_frete, 12.5 AS dias_entrega,
                4.09 AS nota_media
        """)
        con.execute("CREATE TABLE marts.recompra AS SELECT 100.0 AS pct_clientes, 1 AS pedidos_por_cliente")
        con.execute("CREATE TABLE marts.entrega_no_prazo AS SELECT 100.0 AS pct_no_prazo")
        con.execute("""
            CREATE TABLE marts.vendas_mensais AS
            SELECT DATE '2017-01-01' AS mes, 2 AS pedidos, 50.0 AS receita
            UNION ALL SELECT DATE '2018-08-01', 3, 75.0
        """)
        con.execute("CREATE TABLE marts.top_categorias AS SELECT 'casa' AS categoria, 20.0 AS receita")
        con.execute("CREATE TABLE marts.mix_pagamento AS SELECT 'cartao' AS tipo, 100.0 AS pct_valor")
        con.execute("CREATE TABLE marts.ticket_medio_por_estado AS SELECT 'SP' AS uf, 25.5 AS ticket_medio")
        con.execute("CREATE TABLE marts.clientes_por_uf AS SELECT 'SP' AS uf, 2 AS clientes")
        con.execute("CREATE TABLE marts.nota_por_categoria AS SELECT 'casa' AS categoria, 4.0 AS nota_media, 1 AS posicao_pior")
        con.execute("CREATE TABLE marts.vendedores_pareto AS SELECT 'v1' AS vendedor_id, 1 AS posicao, 100.0 AS pct_acumulado")
    finally:
        con.close()


def test_relatorio_gera_html_estavel_exceto_rodape(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(relatorio, "__file__", str(tmp_path / "relatorio.py"))
    _criar_marts_inventados(tmp_path / "olist.duckdb")

    relatorio.main()
    primeiro = (tmp_path / "relatorio.html").read_text(encoding="utf-8")
    saida = capsys.readouterr().out
    assert str(tmp_path / "relatorio.html") in saida
    assert "Tamanho:" in saida
    assert len(primeiro.encode("utf-8")) < 200 * 1024
    assert "R$ 25,50" in primeiro
    assert "1,25%" in primeiro
    assert "jan/2017 a ago/2018" in primeiro
    assert primeiro.count("cdn.plot.ly") == 1
    assert all(f'id="g{i:02d}"' in primeiro for i in range(1, 8))
    assert "Dados de " in primeiro

    relatorio.main()
    segundo = (tmp_path / "relatorio.html").read_text(encoding="utf-8")
    rodape = re.compile(r"Dados de \d{2}/\d{2}/\d{4} \d{2}:\d{2}")
    assert rodape.sub("Dados de DATA", primeiro) == rodape.sub("Dados de DATA", segundo)
