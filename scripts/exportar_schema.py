"""Exporta a estrutura REAL do banco (sem dados) para banco/schema_exportado.sql.

Uso (na pasta do projeto, com o ambiente virtual ativado):
    python -m scripts.exportar_schema

Usa o mysqldump e as credenciais do .env. A senha é passada por variável de ambiente
(MYSQL_PWD), nunca na linha de comando. Compare o resultado com banco/schema.sql
(reconstruído a partir do código) e, se estiver correto, versione o arquivo exportado.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.config import Config

DESTINO = Path("banco/schema_exportado.sql")


def main():
    if not shutil.which("mysqldump"):
        sys.exit("mysqldump não encontrado. Instale o cliente do MariaDB/MySQL ou rode o comando manualmente.")
    comando = ["mysqldump", "--no-data", "--routines", "--triggers", "--skip-comments", "--skip-add-drop-table",
               "-h", Config.DB_HOST, "-P", str(Config.DB_PORT), "-u", Config.DB_USER, Config.DB_NAME]
    ambiente = {**os.environ, "MYSQL_PWD": Config.DB_PASSWORD}
    resultado = subprocess.run(comando, env=ambiente, capture_output=True, text=True)
    if resultado.returncode != 0:
        sys.exit(f"mysqldump falhou: {resultado.stderr.strip()}")
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(resultado.stdout, encoding="utf-8")
    print(f"Estrutura exportada para {DESTINO} ({resultado.stdout.count('CREATE TABLE')} tabelas).")


if __name__ == "__main__":
    main()
