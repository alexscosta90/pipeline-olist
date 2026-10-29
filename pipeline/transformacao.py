"""Transformação de raw para refined, conforme a spec abaixo.

Escopo: lê pedidos, itens_pedido, pagamentos, clientes, vendedores, produtos,
traducao_categorias e avaliacoes de raw; geolocalizacao fica fora porque não é
usada nos dashboards nem nos marts do curso. Os nomes e colunas seguem o mapa
literal em COLUNAS: nenhuma coluna é descartada, para manter JOINs claros.

Tipos: datas com hora são TIMESTAMP via strptime no formato especificado;
data_entrega_prevista é DATE porque sua hora é sempre zero; data_criacao fica
TIMESTAMP para preservar granularidade. Valores monetários usam DECIMAL(12,2)
para precisão e margem; medidas e contagens usam INTEGER; identificadores e
CEP ficam VARCHAR para não perder zeros à esquerda.

Conversões usam CAST/strptime que falham. Se houver valor inválido, imprime
tabela, coluna e exemplo e termina com código 1; não fabrica nulos com TRY_CAST.
Duplicatas idênticas são reduzidas a uma ocorrência e contadas; chaves repetidas
com conteúdo diferente interrompem o processo para evitar escolha silenciosa.
Nulos são preservados, exceto pagamentos sem valor, que não representam uma
transação válida. A saída informa nulos mantidos por coluna.

Cada destino é recriado, nunca acrescentado, para permitir reexecução idempotente.
Antes da transformação, as oito fontes são verificadas. A saída UTF-8 apresenta
contagens consultadas no banco, com milhar separado por ponto e total final.
"""

import sys

from pipeline.db import conectar, criar_schema


# (origem, destino, tipo); texto é mantido sem conversão.
COLUNAS = {
    "pedidos": [
        ("order_id", "pedido_id", "VARCHAR"), ("customer_id", "cliente_id", "VARCHAR"),
        ("order_status", "status", "VARCHAR"),
        ("order_purchase_timestamp", "data_compra", "TIMESTAMP"),
        ("order_approved_at", "data_aprovacao", "TIMESTAMP"),
        ("order_delivered_carrier_date", "data_envio_transportadora", "TIMESTAMP"),
        ("order_delivered_customer_date", "data_entrega_cliente", "TIMESTAMP"),
        ("order_estimated_delivery_date", "data_entrega_prevista", "DATE"),
    ],
    "itens_pedido": [
        ("order_id", "pedido_id", "VARCHAR"), ("order_item_id", "item_seq", "INTEGER"),
        ("product_id", "produto_id", "VARCHAR"), ("seller_id", "vendedor_id", "VARCHAR"),
        ("shipping_limit_date", "data_limite_envio", "TIMESTAMP"),
        ("price", "preco", "DECIMAL(12,2)"), ("freight_value", "frete", "DECIMAL(12,2)"),
    ],
    "pagamentos": [
        ("order_id", "pedido_id", "VARCHAR"),
        ("payment_sequential", "pagamento_seq", "INTEGER"),
        ("payment_type", "tipo", "VARCHAR"),
        ("payment_installments", "parcelas", "INTEGER"),
        ("payment_value", "valor", "DECIMAL(12,2)"),
    ],
    "clientes": [
        ("customer_id", "cliente_id", "VARCHAR"),
        ("customer_unique_id", "cliente_unico_id", "VARCHAR"),
        ("customer_zip_code_prefix", "cep_prefixo", "VARCHAR"),
        ("customer_city", "cidade", "VARCHAR"), ("customer_state", "estado", "VARCHAR"),
    ],
    "vendedores": [
        ("seller_id", "vendedor_id", "VARCHAR"),
        ("seller_zip_code_prefix", "cep_prefixo", "VARCHAR"),
        ("seller_city", "cidade", "VARCHAR"), ("seller_state", "estado", "VARCHAR"),
    ],
    "produtos": [
        ("product_id", "produto_id", "VARCHAR"),
        ("product_category_name", "categoria", "VARCHAR"),
        ("product_name_lenght", "tamanho_nome", "INTEGER"),
        ("product_description_lenght", "tamanho_descricao", "INTEGER"),
        ("product_photos_qty", "qtd_fotos", "INTEGER"),
        ("product_weight_g", "peso_g", "INTEGER"),
        ("product_length_cm", "comprimento_cm", "INTEGER"),
        ("product_height_cm", "altura_cm", "INTEGER"),
        ("product_width_cm", "largura_cm", "INTEGER"),
    ],
    "categorias_traducao": [
        ("product_category_name", "categoria", "VARCHAR"),
        ("product_category_name_english", "categoria_en", "VARCHAR"),
    ],
    "avaliacoes": [
        ("review_id", "avaliacao_id", "VARCHAR"), ("order_id", "pedido_id", "VARCHAR"),
        ("review_score", "nota", "INTEGER"),
        ("review_comment_title", "titulo", "VARCHAR"),
        ("review_comment_message", "comentario", "VARCHAR"),
        ("review_creation_date", "data_criacao", "TIMESTAMP"),
        ("review_answer_timestamp", "data_resposta", "TIMESTAMP"),
    ],
}

CHAVES = {
    "pedidos": ("pedido_id",), "itens_pedido": ("pedido_id", "item_seq"),
    "pagamentos": ("pedido_id", "pagamento_seq"), "clientes": ("cliente_id",),
    "vendedores": ("vendedor_id",), "produtos": ("produto_id",),
    "categorias_traducao": ("categoria",),
    "avaliacoes": ("avaliacao_id", "pedido_id"),
}


def _expressao(origem: str, destino: str, tipo: str) -> str:
    col = f'"{origem}"'
    if tipo == "TIMESTAMP":
        return f"strptime({col}, '%Y-%m-%d %H:%M:%S') AS \"{destino}\""
    if tipo == "DATE":
        return f"CAST({col} AS DATE) AS \"{destino}\""
    if tipo != "VARCHAR":
        return f"CAST({col} AS {tipo}) AS \"{destino}\""
    return f"{col} AS \"{destino}\""


def _nome_origem(destino: str) -> str:
    return "traducao_categorias" if destino == "categorias_traducao" else destino


def _select(destino: str, mapa) -> str:
    origem = _nome_origem(destino)
    expressoes = ", ".join(_expressao(*item) for item in mapa)
    filtro = ' WHERE "payment_value" IS NOT NULL' if destino == "pagamentos" else ""
    return f'SELECT DISTINCT {expressoes} FROM raw."{origem}"{filtro}'


def _validar_conversoes(con, origem: str, destino: str, mapa) -> None:
    for coluna, nome, tipo in mapa:
        if tipo in ("VARCHAR",):
            continue
        expr = (f"strptime(\"{coluna}\", '%Y-%m-%d %H:%M:%S')" if tipo == "TIMESTAMP"
                else f'CAST("{coluna}" AS {tipo})')
        try:
            con.execute(f'SELECT {expr} FROM raw."{origem}"').fetchall()
        except Exception:
            # A validação linha a linha localiza o primeiro exemplo que falha.
            for (valor,) in con.execute(
                f'SELECT DISTINCT "{coluna}" FROM raw."{origem}" WHERE "{coluna}" IS NOT NULL'
            ).fetchall():
                try:
                    con.execute(f"SELECT {expr.replace(chr(34) + coluna + chr(34), '?')}", [valor]).fetchone()
                except Exception:
                    print(f"Conversão inválida em raw.{origem}.{coluna}: {valor!r}")
                    raise SystemExit(1)
            print(f"Falha de conversão em raw.{origem}.{coluna}")
            raise SystemExit(1)


def _transformar(con, destino: str, mapa) -> tuple[int, int, int]:
    origem = _nome_origem(destino)
    _validar_conversoes(con, origem, destino, mapa)
    select = _select(destino, mapa)
    bruto = con.execute(f'SELECT COUNT(*) FROM raw."{origem}"').fetchone()[0]
    chave = CHAVES[destino]
    chave_sql = ", ".join(f'"{c}"' for c in chave)
    saida_calculada = con.execute(
        f"SELECT COUNT(*) FROM ({select}) AS saida"
    ).fetchone()[0]
    filtro_contagem = ' WHERE "payment_value" IS NOT NULL' if destino == "pagamentos" else ""
    linhas_apos_filtro = con.execute(
        f'SELECT COUNT(*) FROM raw."{origem}"{filtro_contagem}'
    ).fetchone()[0]
    # Chave repetida com mais de uma linha distinta é ambígua.
    conflitos = con.execute(
        f'SELECT {chave_sql}, COUNT(*) FROM ({select}) AS saida '
        f'GROUP BY {chave_sql} HAVING COUNT(*) > 1'
    ).fetchall()
    if conflitos:
        print(f"Chaves conflitantes em {destino}:")
        for conflito in conflitos:
            valores_chave = conflito[:-1]
            predicado = " AND ".join(f'"{c}" IS NOT DISTINCT FROM ?' for c in chave)
            linhas = con.execute(
                f'SELECT * FROM ({select}) AS saida WHERE {predicado}', valores_chave
            ).fetchall()
            print(f"  chave {valores_chave}:")
            for linha in linhas:
                print(f"    {linha}")
        raise SystemExit(1)
    duplicatas = linhas_apos_filtro - saida_calculada
    con.execute(f'CREATE OR REPLACE TABLE refined."{destino}" AS {select}')
    saida = con.execute(f'SELECT COUNT(*) FROM refined."{destino}"').fetchone()[0]
    return bruto, saida, duplicatas


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    con = conectar()
    try:
        existentes = {r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
        ).fetchall()}
        faltantes = [_nome_origem(nome) for nome in COLUNAS if _nome_origem(nome) not in existentes]
        if faltantes:
            print("Tabelas ausentes em raw: " + ", ".join(faltantes) + ". Rode a ingestão primeiro.")
            raise SystemExit(1)
        criar_schema(con, "refined")
        total = 0
        for tabela, mapa in COLUNAS.items():
            bruto, saida, duplicatas = _transformar(con, tabela, mapa)
            total += saida
            print(f"refined.{tabela:<21} {bruto:,} -> {saida:,} linhas  ({duplicatas:,} duplicatas)".replace(",", "."))
            nulos = []
            for _, coluna, _ in mapa:
                qtd = con.execute(f'SELECT COUNT(*) FROM refined."{tabela}" WHERE "{coluna}" IS NULL').fetchone()[0]
                if qtd:
                    nulos.append(f"{coluna} {qtd:,}".replace(",", "."))
            if nulos:
                print("    nulos mantidos: " + ", ".join(nulos))
        print(f"Total: {total:,} linhas".replace(",", "."))
    finally:
        con.close()


if __name__ == "__main__":
    main()
