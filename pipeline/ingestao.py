"""Ingestão fiel dos nove arquivos Olist no schema raw.

O mapa literal mantém os nomes de destino em português para facilitar os
JOINs das aulas. Todos os arquivos são verificados antes de abrir o banco para
evitar uma ingestão parcial que pareça completa. A leitura usa UTF-8 declarado
e trabalha diretamente nos gzip; dtype=str preserva, por exemplo, zeros à
esquerda. Só campos realmente vazios viram nulos, sem tratar textos como "NA"
como ausência. Nenhuma coluna ou linha é modificada ou removida. Cada tabela é
substituída para que reexecutar seja idempotente. As contagens exibidas vêm do
banco, que é a conferência disponível nesta etapa. O stdout é UTF-8 porque o
Prompt de Comando do Windows pode exibir acentos incorretamente sem isso.
"""

import sys

import pandas as pd

from pipeline.db import PASTA_RAW, conectar, criar_schema, gravar


ARQUIVOS_TABELAS = (
    ("olist_orders_dataset.csv.gz", "pedidos"),
    ("olist_order_items_dataset.csv.gz", "itens_pedido"),
    ("olist_order_payments_dataset.csv.gz", "pagamentos"),
    ("olist_order_reviews_dataset.csv.gz", "avaliacoes"),
    ("olist_customers_dataset.csv.gz", "clientes"),
    ("olist_sellers_dataset.csv.gz", "vendedores"),
    ("olist_products_dataset.csv.gz", "produtos"),
    ("product_category_name_translation.csv.gz", "traducao_categorias"),
    ("olist_geolocation_dataset.csv.gz", "geolocalizacao"),
)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ausentes = [nome for nome, _ in ARQUIVOS_TABELAS if not (PASTA_RAW / nome).is_file()]
    if ausentes:
        print(f"Arquivos ausentes em {PASTA_RAW}:")
        for nome in ausentes:
            print(f"- {nome}")
        sys.exit(1)

    con = conectar()
    try:
        criar_schema(con, "raw")
        total = 0
        for arquivo, tabela in ARQUIVOS_TABELAS:
            df = pd.read_csv(
                PASTA_RAW / arquivo,
                compression="gzip",
                encoding="utf-8",
                dtype=str,
                keep_default_na=False,
                na_values=[""],
            )
            contagem = gravar(con, df, "raw", tabela)
            total += contagem
            print(f"raw.{tabela}: {contagem:,}".replace(",", "."))

        print(f"Total: {total:,}".replace(",", "."))
    finally:
        con.close()


if __name__ == "__main__":
    main()
