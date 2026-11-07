"""Geração de CSV para abrir direto no Excel em português (separador ; e acentos preservados)."""
import csv
import io
from datetime import date, datetime
from decimal import Decimal

_PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")


def csv_seguro(texto):
    """Impede injeção de fórmula: células de texto que começam com = + - @ ganham um apóstrofo."""
    texto = str(texto)
    return "'" + texto if texto.startswith(_PERIGOSOS) else texto


def celula(valor):
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, Decimal):
        return f"{valor:.2f}".replace(".", ",")
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return csv_seguro(valor)


def gerar_csv(colunas, linhas):
    """colunas: [(chave, título)]; linhas: lista de dicts. Devolve texto com BOM UTF-8."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow([titulo for _, titulo in colunas])
    for linha in linhas:
        escritor.writerow([celula(linha.get(chave)) for chave, _ in colunas])
    return "\ufeff" + saida.getvalue()
