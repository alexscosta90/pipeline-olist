from datetime import date

import duckdb
import pandas as pd
import pytest

import painel


def test_formatadores_usam_formato_brasileiro():
    assert painel.reais(1234.5) == "R$ 1.234,50"
    assert painel.pct(12.34, casas=2) == "12,34%"
    assert painel.numero(1234.5, casas=1) == "1.234,5"


def test_ler_busca_apenas_marts_solicitados_e_fecha_conexao(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    con = duckdb.connect("olist.duckdb")
    try:
        con.execute("CREATE SCHEMA marts")
        con.execute("CREATE TABLE marts.amostra AS SELECT 5 AS valor")
    finally:
        con.close()

    dados = painel.ler(("amostra",))
    assert dados["amostra"]["valor"].tolist() == [5]
    # O banco deve voltar a aceitar escrita depois que ler fecha a conexão.
    con = duckdb.connect("olist.duckdb")
    try:
        con.execute("CREATE TABLE marts.nova AS SELECT 6 AS valor")
        assert con.execute("SELECT valor FROM marts.nova").fetchone() == (6,)
    finally:
        con.close()


def test_ler_informa_todas_as_tabelas_ausentes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    con = duckdb.connect("olist.duckdb")
    con.close()

    with pytest.raises(painel.MartsAusentesError) as erro:
        painel.ler(("um", "dois"))
    assert erro.value.nomes == ["um", "dois"]


def test_cada_grafico_retorna_figura_com_pontos_das_linhas():
    mes = pd.DataFrame({"mes": [date(2017, 1, 1), date(2017, 2, 1)], "receita": [10, 20]})
    categoria = pd.DataFrame({"categoria": ["a", "b"], "receita": [10, 20]})
    mix = pd.DataFrame({"tipo": ["cartao", "boleto"], "pct_valor": [60, 40]})
    uf_ticket = pd.DataFrame({"uf": ["SP", "RJ"], "ticket_medio": [100, 200]})
    uf_clientes = pd.DataFrame({"uf": ["SP", "RJ"], "clientes": [20, 10]})
    notas = pd.DataFrame({"categoria": ["a", "b"], "nota_media": [3.5, 4.5], "posicao_pior": [1, 2]})
    pareto = pd.DataFrame({"posicao": [1, 2], "pct_acumulado": [60, 100]})

    graficos = [
        (painel.grafico_vendas_mensais(mes), 2),
        (painel.grafico_top_categorias(categoria), 2),
        (painel.grafico_mix_pagamento(mix), 2),
        (painel.grafico_ticket_por_uf(uf_ticket), 2),
        (painel.grafico_clientes_por_uf(uf_clientes), 2),
        (painel.grafico_nota_categoria(notas), 2),
        (painel.grafico_pareto_vendedores(pareto), 2),
    ]
    for figura, pontos in graficos:
        assert sum(len(traco.x) for traco in figura.data if traco.x is not None) == pontos
