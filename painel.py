"""Spec do painel de indicadores Olist e motivo das decisões.

Leitura: ler(marts) executa somente SELECT * FROM marts.<nome> e retorna um
dicionário nome -> DataFrame. A conexão é read_only e fecha dentro de ler():
isso libera o arquivo DuckDB para que pipeline.marts possa gravar enquanto o
painel continua aberto. A conexão não fica em cache.

Cálculos: os indicadores de negócio devem vir prontos dos marts para manter a
SQL como fonte da regra. A camada de apresentação só formata valores, ordena,
seleciona e filtra linhas. A única conta permitida é 100 menos a participação
de clientes com uma compra, pois o mart recompra guarda esse complemento.
Formato brasileiro é produzido sem locale para não depender da máquina.

Gráficos: cada função grafico_* recebe o DataFrame do mart e devolve uma figura
Plotly; isso permite reutilizar as figuras em outros relatórios. Os gráficos
exibem os dez primeiros itens nos rankings indicados, usam uma cor e mostram
unidades nos eixos. O Pareto conserva todos os vendedores e marca 80%.

Período: o seletor usa os meses existentes em vendas_mensais e abre entre
janeiro de 2017 e agosto de 2018. Ele filtra somente as linhas do gráfico
mensal; cartões e demais gráficos representam o período inteiro, pois alterar
esses indicadores exigiria uma nova regra SQL.

Layout e atualização: app.py usa página ampla, sete cartões e duas faixas com
três gráficos cada. Os DataFrames são armazenados com st.cache_data. O botão
Recarregar dados limpa o cache. Banco ausente ou marts necessários ausentes
devem gerar mensagem com os nomes e o comando para executar pipeline.marts.
"""

from collections.abc import Iterable

import duckdb
import pandas as pd
import plotly.express as px


COR = "#D97732"


class MartsAusentesError(RuntimeError):
    """Indica quais tabelas esperadas não existem no schema marts."""

    def __init__(self, nomes: list[str]):
        self.nomes = nomes
        super().__init__(", ".join(nomes))


def ler(marts: Iterable[str]) -> dict[str, pd.DataFrame]:
    """Lê os marts solicitados e fecha a conexão antes de retornar."""
    con = duckdb.connect("olist.duckdb", read_only=True)
    dados: dict[str, pd.DataFrame] = {}
    ausentes = []
    try:
        for nome in marts:
            try:
                dados[nome] = con.execute(f"SELECT * FROM marts.{nome}").fetchdf()
            except duckdb.CatalogException:
                ausentes.append(nome)
    finally:
        con.close()

    if ausentes:
        raise MartsAusentesError(ausentes)
    return dados


def _numero_br(valor, casas: int) -> str:
    formatado = f"{valor:,.{casas}f}"
    return formatado.replace(",", "§").replace(".", ",").replace("§", ".")


def reais(valor, casas: int = 2) -> str:
    return f"R$ {_numero_br(valor, casas)}"


def pct(valor, casas: int = 1) -> str:
    return f"{_numero_br(valor, casas)}%"


def numero(valor, casas: int = 0) -> str:
    return _numero_br(valor, casas)


def grafico_vendas_mensais(df: pd.DataFrame):
    fig = px.line(
        df.sort_values("mes"),
        x="mes",
        y="receita",
        markers=True,
        color_discrete_sequence=[COR],
    )
    fig.update_layout(
        title="01 · Faturamento mensal",
        xaxis_title="Mês",
        yaxis_title="Receita (R$)",
    )
    fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
    return fig


def grafico_top_categorias(df: pd.DataFrame):
    dados = df.sort_values("receita", ascending=False).head(10)
    fig = px.bar(
        dados,
        x="receita",
        y="categoria",
        orientation="h",
        color_discrete_sequence=[COR],
    )
    fig.update_layout(
        title="02 · Receita por categoria",
        xaxis_title="Receita (R$)",
        yaxis_title="Categoria",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
    return fig


def grafico_mix_pagamento(df: pd.DataFrame):
    dados = df.sort_values("pct_valor", ascending=False)
    fig = px.bar(
        dados,
        x="tipo",
        y="pct_valor",
        color_discrete_sequence=[COR],
    )
    fig.update_layout(
        title="07 · Mix de pagamento",
        xaxis_title="Tipo de pagamento",
        yaxis_title="Participação do valor (%)",
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def grafico_ticket_por_uf(df: pd.DataFrame):
    dados = df.sort_values("ticket_medio", ascending=False)
    fig = px.bar(
        dados,
        x="ticket_medio",
        y="uf",
        orientation="h",
        color_discrete_sequence=[COR],
    )
    fig.update_layout(
        title="06 · Ticket médio por UF",
        xaxis_title="Ticket médio (R$)",
        yaxis_title="UF do cliente",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
    return fig


def grafico_clientes_por_uf(df: pd.DataFrame):
    dados = df.sort_values("clientes", ascending=False)
    fig = px.bar(
        dados,
        x="clientes",
        y="uf",
        orientation="h",
        color_discrete_sequence=[COR],
    )
    fig.update_layout(
        title="12 · Clientes por UF",
        xaxis_title="Clientes únicos na UF",
        yaxis_title="UF",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def grafico_nota_categoria(df: pd.DataFrame):
    dados = df.sort_values("posicao_pior").head(10)
    fig = px.scatter(
        dados,
        x="nota_media",
        y="categoria",
        color_discrete_sequence=[COR],
    )
    fig.update_layout(
        title="04 · Nota por categoria",
        xaxis_title="Nota média (0 a 5)",
        yaxis_title="Categoria",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def grafico_pareto_vendedores(df: pd.DataFrame):
    dados = df.sort_values("posicao")
    fig = px.line(
        dados,
        x="posicao",
        y="pct_acumulado",
        color_discrete_sequence=[COR],
    )
    fig.add_hline(y=80, line_dash="dash", line_color=COR)
    fig.update_layout(
        title="09 · Concentração de vendedores",
        xaxis_title="Posição do vendedor",
        yaxis_title="Receita acumulada (%)",
    )
    fig.update_yaxes(ticksuffix="%")
    return fig
