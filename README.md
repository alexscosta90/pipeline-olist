# Pipeline Olist | Engenharia de Dados e Dashboard

Projeto prático de Engenharia de Dados desenvolvido durante meus estudos, utilizando dados reais de e-commerce brasileiro disponibilizados pela Olist.

O objetivo foi construir um pipeline de dados de ponta a ponta, desde a ingestão e transformação dos arquivos CSV até a criação de indicadores de negócio e sua visualização em um dashboard interativo.

O projeto foi desenvolvido com base nas aulas do professor **Carlos Oliveira**, colocando em prática conceitos de Python, SQL, modelagem de dados e visualização.

### 🚀 Dashboard online

O resultado do projeto pode ser acessado pelo Streamlit:

**[Acessar Dashboard Olist](https://alex-olist.streamlit.app/)**

O painel apresenta indicadores e análises sobre vendas, clientes, entregas, avaliações e desempenho da operação.

## 🛠️ Tecnologias utilizadas

- **Python:** desenvolvimento e execução do pipeline.
- **DuckDB:** armazenamento e processamento analítico dos dados.
- **SQL:** transformação dos dados e construção dos indicadores.
- **Pandas:** leitura e manipulação dos arquivos CSV.
- **Streamlit:** criação do dashboard interativo.
- **Plotly:** visualização dos dados em gráficos.
- **uv:** gerenciamento do ambiente e das dependências.
- **Git e GitHub:** versionamento e publicação do projeto.

## 🏗️ Arquitetura do pipeline

Os dados são organizados em três camadas:

**RAW → REFINED → MARTS → DASHBOARD**

| Camada | Descrição |
|---|---|
| RAW | Ingestão dos arquivos originais da Olist, preservando os dados de origem. |
| REFINED | Tratamento dos dados, conversão de tipos, padronização e remoção de duplicatas. |
| MARTS | Consultas SQL com indicadores e informações organizadas para análise. |
| Dashboard | Visualização interativa dos resultados utilizando Streamlit e Plotly. |

Essa organização permite separar a preparação dos dados das regras de negócio e da apresentação dos resultados.

## 📊 Indicadores desenvolvidos

Foram construídos 12 MARTS SQL, incluindo análises de:

- Faturamento mensal e evolução das vendas.
- Categorias de produtos com maior receita.
- Percentual de entregas realizadas no prazo.
- Avaliações dos clientes por categoria.
- Recompra e comportamento dos consumidores.
- Ticket médio por estado.
- Distribuição das formas de pagamento.
- Relação entre prazo de entrega e avaliação.
- Concentração das vendas por vendedor (Pareto).
- Tempo médio de entrega por estado.
- KPIs gerais da operação.
- Quantidade de clientes únicos por UF.

Esses indicadores alimentam o dashboard e ajudam a explorar diferentes aspectos da operação do e-commerce.

## 📁 Estrutura do projeto

```text
pipeline-olist/
├── pipeline/
│   ├── db.py
│   ├── ingestao.py
│   ├── transformacao.py
│   └── marts.py
├── raw/
│   └── arquivos Olist (.csv.gz)
├── sql/
│   └── marts/
│       ├── 01_vendas_mensais.sql
│       ├── ...
│       ├── 11_kpis.sql
│       └── 12_clientes_por_uf.sql
├── app.py
├── painel.py
├── ui.py
├── pyproject.toml
└── uv.lock
```

## ▶️ Como executar

Clone o repositório:

```bash
git clone https://github.com/alexscosta90/pipeline-olist.git
cd pipeline-olist
```

Instale as dependências com o uv:

```bash
uv sync
```

Execute as etapas do pipeline na sequência:

**1. Ingestão dos dados**

```bash
uv run python -m pipeline.ingestao
```

**2. Transformação dos dados**

```bash
uv run python -m pipeline.transformacao
```

**3. Construção dos MARTS**

```bash
uv run python -m pipeline.marts
```

**4. Execução do dashboard**

```bash
uv run streamlit run app.py
```

Para executar o pipeline, os nove arquivos originais `.csv.gz` precisam estar disponíveis na pasta `raw/`.

## 📚 Fonte dos dados

O projeto utiliza o [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), disponível no Kaggle.

O conjunto contém informações sobre pedidos, produtos, clientes, vendedores, pagamentos, avaliações e entregas do comércio eletrônico brasileiro.

Os dados originais são mantidos sem alterações na camada RAW, permitindo rastrear as transformações realizadas ao longo do pipeline.

## 🎓 Referências e créditos

Projeto desenvolvido como atividade prática de aprendizagem, seguindo o material e as orientações do professor **Carlos Oliveira**.

O conteúdo das aulas, a proposta do projeto e a estrutura-base do dashboard foram disponibilizados pelo professor.

- [Guia do curso Pipeline Olist](https://ckoliveiraa.github.io/pipeline-olist/)
- [Repositório original do professor](https://github.com/ckoliveiraa/pipeline-olist)

A implementação deste repositório faz parte da minha jornada de estudos em Engenharia de Dados e Inteligência Artificial, com foco no desenvolvimento de habilidades práticas em construção de pipelines, SQL, processamento e análise de dados.

---

### 👨‍💻 Autor

**Alex Santos da Costa**

Engenheiro Eletricista | Pós-graduando em Engenharia de Dados e Inteligência Artificial

[LinkedIn](https://www.linkedin.com/in/alexsantosdacosta/) | [GitHub](https://github.com/alexscosta90) | [Dashboard Olist](https://alex-olist.streamlit.app/)
