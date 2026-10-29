"""Abre a UI local do DuckDB para explorar o banco do projeto.

O caminho do banco é o mesmo da ingestão. A verificação anterior à conexão
evita criar um arquivo vazio que pareça uma ingestão incompleta. A extensão
ui é instalada e carregada explicitamente para deixar clara sua dependência;
start_ui abre o navegador e mantém o servidor ligado enquanto esta conexão
vive. O processo espera até Ctrl+C, fecha a conexão para liberar o lock e
configura stdout como UTF-8 para exibir corretamente os acentos no Windows.
"""

import sys
from pathlib import Path
from threading import Event

import duckdb


CAMINHO_BANCO = Path(__file__).resolve().parent / "olist.duckdb"
URL = "http://localhost:4213"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not CAMINHO_BANCO.is_file():
        print(
            f"Banco não encontrado em {CAMINHO_BANCO}. "
            "É preciso rodar a ingestão antes."
        )
        sys.exit(1)

    con = duckdb.connect(str(CAMINHO_BANCO))
    try:
        con.execute("INSTALL ui")
        con.execute("LOAD ui")
        con.execute("CALL start_ui()")
        print(f"UI disponível em {URL}")
        print("Ctrl+C para encerrar")
        Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        con.close()


if __name__ == "__main__":
    main()
