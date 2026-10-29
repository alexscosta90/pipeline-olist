"""Executor dos marts, conforme a spec.

Escopo: lê consultas de sql/marts e grava tabelas somente no schema marts.
Cada arquivo SQL define integralmente a regra de negócio da tabela; o Python
somente remove espaços externos e um ponto e vírgula final antes de executá-lo.

Mapeamento: arquivos no formato NN_nome.sql viram marts.nome. Todos os arquivos
são lidos em ordem alfabética. Arquivos sem prefixo numérico de dois dígitos ou
nomes de tabela duplicados interrompem a execução antes de qualquer SQL de mart.

Recriação: o schema marts é apagado e recriado dentro de uma única transação.
Assim, marts removidos do diretório também somem do banco, e qualquer falha
restaura integralmente o schema da última execução bem-sucedida.

Pré-requisito: as oito tabelas de refined precisam existir; se faltarem, a
mensagem orienta executar pipeline.transformacao antes dos marts.

Saída: imprime uma linha por tabela com contagem consultada no banco, separador
de milhar por ponto, e um total final. stdout é configurado como UTF-8.

Falhas: ausência de arquivos, SQL inválido ou mart sem linhas termina com
código 1. Em erro de SQL, informa arquivo e mensagem DuckDB; os arquivos
seguintes não são executados.
"""

import re
import sys
from pathlib import Path

from pipeline.db import conectar


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_MARTS = RAIZ_PROJETO / "sql" / "marts"
TABELAS_REFINED = (
    "pedidos",
    "itens_pedido",
    "pagamentos",
    "clientes",
    "vendedores",
    "produtos",
    "categorias_traducao",
    "avaliacoes",
)
PADRAO_ARQUIVO = re.compile(r"^\d{2}_(.+)\.sql$")


def _arquivos_e_nomes() -> list[tuple[Path, str]]:
    arquivos = sorted(PASTA_MARTS.glob("*.sql"), key=lambda p: p.name)
    if not arquivos:
        print(f"Nenhum arquivo .sql encontrado em {PASTA_MARTS}")
        raise SystemExit(1)

    invalidos = [arquivo.name for arquivo in arquivos if not PADRAO_ARQUIVO.fullmatch(arquivo.name)]
    if invalidos:
        print("Arquivos sem prefixo NN_: " + ", ".join(invalidos))
        raise SystemExit(1)

    mapeados = [
        (arquivo, PADRAO_ARQUIVO.fullmatch(arquivo.name).group(1))
        for arquivo in arquivos
    ]
    nomes: dict[str, list[str]] = {}
    for arquivo, nome in mapeados:
        nomes.setdefault(nome, []).append(arquivo.name)
    duplicados = [
        f"{nome}: {', '.join(arquivos_com_nome)}"
        for nome, arquivos_com_nome in nomes.items()
        if len(arquivos_com_nome) > 1
    ]
    if duplicados:
        print("Arquivos com nomes de tabela duplicados: " + "; ".join(duplicados))
        raise SystemExit(1)
    return mapeados


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    con = conectar()
    try:
        existentes = {
            linha[0]
            for linha in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'refined'"
            ).fetchall()
        }
        faltantes = [nome for nome in TABELAS_REFINED if nome not in existentes]
        if faltantes:
            print(
                "Tabelas ausentes em refined: " + ", ".join(faltantes)
                + ". Rode: uv run python -m pipeline.transformacao"
            )
            raise SystemExit(1)

        arquivos = _arquivos_e_nomes()
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute("DROP SCHEMA IF EXISTS marts CASCADE")
            con.execute("CREATE SCHEMA marts")
            total_linhas = 0
            for arquivo, nome in arquivos:
                sql = arquivo.read_text(encoding="utf-8").strip()
                if sql.endswith(";"):
                    sql = sql[:-1].rstrip()
                try:
                    con.execute(f'CREATE TABLE marts."{nome}" AS {sql}')
                except Exception as erro:
                    print(f"Erro em {arquivo.name}: {erro}")
                    raise SystemExit(1) from erro

                linhas = con.execute(
                    f'SELECT COUNT(*) FROM marts."{nome}"'
                ).fetchone()[0]
                if linhas == 0:
                    print(f"Mart vazio: {arquivo.name}")
                    raise SystemExit(1)
                total_linhas += linhas
                print(f"✓ marts.{nome:<26} {linhas:,} linhas".replace(",", "."))

            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise

        print(
            f"Total: {len(arquivos):,} marts, {total_linhas:,} linhas".replace(",", ".")
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
