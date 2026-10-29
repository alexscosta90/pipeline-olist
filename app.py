from pathlib import Path

import streamlit as st

import painel


MARTS = (
    "kpis",
    "recompra",
    "entrega_no_prazo",
    "vendas_mensais",
    "top_categorias",
    "mix_pagamento",
    "ticket_medio_por_estado",
    "clientes_por_uf",
    "nota_por_categoria",
    "vendedores_pareto",
)
COMANDO_MARTS = "uv run python -m pipeline.marts"


st.set_page_config(
    page_title="Olist · visão da operação",
    page_icon=":material/monitoring:",
    layout="wide",
)


@st.cache_data(show_spinner="Lendo os marts do DuckDB...")
def carregar_dados():
    return painel.ler(MARTS)


def obter_dados():
    caminho_banco = Path(__file__).resolve().with_name("olist.duckdb")
    if not caminho_banco.is_file():
        st.error(f"Banco olist.duckdb não encontrado. Execute `{COMANDO_MARTS}`.")
        st.stop()
    try:
        return carregar_dados()
    except painel.MartsAusentesError as erro:
        st.error(
            f"Marts ausentes: {', '.join(erro.nomes)}. "
            f"Execute `{COMANDO_MARTS}`."
        )
        st.stop()


dados = obter_dados()

col_titulo, col_controles = st.columns([1, 2], vertical_alignment="center")
with col_titulo:
    st.title("Olist · visão da operação")
with col_controles:
    col_periodo, col_recarregar = st.columns([4, 1], vertical_alignment="bottom")
    meses = dados["vendas_mensais"]["mes"].tolist()
    with col_periodo:
        periodo = st.select_slider(
            "Período de faturamento",
            options=meses,
            value=(
                next(mes for mes in meses if mes.year == 2017 and mes.month == 1),
                next(mes for mes in meses if mes.year == 2018 and mes.month == 8),
            ),
            format_func=lambda mes: mes.strftime("%b/%Y"),
        )
        st.caption("Os cartões valem para o período inteiro.")
    with col_recarregar:
        if st.button("Recarregar dados", icon=":material/refresh:"):
            carregar_dados.clear()
            st.rerun()

kpis = dados["kpis"].iloc[0]
clientes_uma_compra = dados["recompra"].loc[
    dados["recompra"]["pedidos_por_cliente"] == 1,
    "pct_clientes",
].iloc[0]
pct_recompra = 100 - clientes_uma_compra
pct_no_prazo = dados["entrega_no_prazo"].iloc[0]["pct_no_prazo"]

with st.container(horizontal=True):
    st.metric("Ticket médio · por pedido", painel.reais(kpis["ticket_medio"]), border=True)
    st.metric(
        "Cancelados · % dos pedidos",
        painel.pct(kpis["pct_cancelados"], casas=2),
        border=True,
    )
    st.metric("Peso do frete · valor total", painel.pct(kpis["pct_frete"]), border=True)
    st.metric("Recompra · clientes com 2+ pedidos", painel.pct(pct_recompra, casas=2), border=True)
    st.metric("No prazo · pedidos entregues", painel.pct(pct_no_prazo), border=True)
    st.metric("Dias até entregar · compra à entrega", f"{painel.numero(kpis['dias_entrega'], 1)} dias", border=True)
    st.metric("Nota média · avaliações", painel.numero(kpis["nota_media"], 2), border=True)

inicio, fim = periodo
vendas_periodo = dados["vendas_mensais"].loc[
    dados["vendas_mensais"]["mes"].between(inicio, fim)
]
st.plotly_chart(
    painel.grafico_vendas_mensais(vendas_periodo),
    width="stretch",
    alt="Faturamento mensal por mês de compra.",
)

col_categoria, col_pagamento, col_ticket = st.columns(3)
with col_categoria:
    st.plotly_chart(
        painel.grafico_top_categorias(dados["top_categorias"]),
        width="stretch",
        alt="As dez categorias com maior receita.",
    )
with col_pagamento:
    st.plotly_chart(
        painel.grafico_mix_pagamento(dados["mix_pagamento"]),
        width="stretch",
        alt="Participação de cada tipo de pagamento no valor total.",
    )
with col_ticket:
    st.plotly_chart(
        painel.grafico_ticket_por_uf(dados["ticket_medio_por_estado"]),
        width="stretch",
        alt="Ticket médio por estado do cliente.",
    )

col_clientes, col_notas, col_pareto = st.columns(3)
with col_clientes:
    st.plotly_chart(
        painel.grafico_clientes_por_uf(dados["clientes_por_uf"]),
        width="stretch",
        alt="Clientes únicos por estado.",
    )
with col_notas:
    st.plotly_chart(
        painel.grafico_nota_categoria(dados["nota_por_categoria"]),
        width="stretch",
        alt="As dez categorias com piores notas médias.",
    )
with col_pareto:
    st.plotly_chart(
        painel.grafico_pareto_vendedores(dados["vendedores_pareto"]),
        width="stretch",
        alt="Receita acumulada por posição dos vendedores, com referência em 80 por cento.",
    )
