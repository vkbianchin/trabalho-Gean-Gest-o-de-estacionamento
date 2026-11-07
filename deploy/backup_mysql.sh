#!/usr/bin/env bash
# Backup diário do banco. Ajuste DB_NAME e o destino. Mantém os últimos 14 dias.
set -euo pipefail
DB_NAME="estacionamento"
DESTINO="/var/backups/parkflow"
mkdir -p "$DESTINO"
ARQUIVO="$DESTINO/${DB_NAME}_$(date +%F_%H%M).sql.gz"
# --single-transaction: cópia consistente sem travar o sistema (tabelas InnoDB).
mysqldump --single-transaction --routines --triggers "$DB_NAME" | gzip > "$ARQUIVO"
chmod 600 "$ARQUIVO"
find "$DESTINO" -name "${DB_NAME}_*.sql.gz" -mtime +14 -delete
echo "Backup gravado em $ARQUIVO"
# IMPORTANTE: copie para fora do servidor e teste a restauração:
#   gunzip < arquivo.sql.gz | mysql estacionamento_teste
