from datetime import date, datetime
from decimal import Decimal

import pytest

from app.exportacao import celula, csv_seguro, gerar_csv
from app.tempo import dias_em_atraso, formatar_duracao, limites_do_periodo, minutos_entre


@pytest.mark.parametrize("minutos,esperado", [
    (0, "0min"), (5, "5min"), (45, "45min"), (60, "1h"), (125, "2h 05min"),
    (1440, "1 dia"), (1500, "1 dia 1h"), (3000, "2 dias 2h"), (1445, "1 dia 05min"),
])
def test_formatar_duracao(minutos, esperado):
    assert formatar_duracao(minutos) == esperado


def test_minutos_entre_arredonda_para_baixo_e_nao_fica_negativo():
    assert minutos_entre(datetime(2026, 10, 30, 10, 0, 0), datetime(2026, 10, 30, 10, 0, 59)) == 0
    assert minutos_entre(datetime(2026, 10, 30, 10, 0), datetime(2026, 10, 30, 12, 35)) == 155
    assert minutos_entre(datetime(2026, 10, 30, 12, 0), datetime(2026, 10, 30, 10, 0)) == 0


def test_limites_do_periodo_incluem_o_ultimo_dia_inteiro():
    ini, lim = limites_do_periodo(date(2026, 10, 1), date(2026, 10, 31))
    assert ini == datetime(2026, 10, 1, 0, 0)
    assert lim == datetime(2026, 11, 1, 0, 0)  # exclusivo: 31/10 23:59 ainda entra


def test_atraso_considera_a_carencia():
    venc, hoje = date(2026, 10, 5), date(2026, 10, 10)
    assert dias_em_atraso(venc, hoje, 0) == 5
    assert dias_em_atraso(venc, hoje, 5) == 0   # ainda dentro da carência
    assert dias_em_atraso(venc, hoje, 3) == 2
    assert dias_em_atraso(date(2026, 10, 20), hoje, 0) == 0  # ainda não venceu
    assert dias_em_atraso(None, hoje, 0) == 0
    assert dias_em_atraso(datetime(2026, 10, 5, 8, 0), hoje, 0) == 5


def test_csv_seguro_bloqueia_formulas():
    assert csv_seguro("=SOMA(A1:A2)") == "'=SOMA(A1:A2)"
    assert csv_seguro("+55 49 99999") == "'+55 49 99999"
    assert csv_seguro("@fulano") == "'@fulano"
    assert csv_seguro("Maria") == "Maria"


def test_celula_formata_tipos():
    assert celula(Decimal("12.5")) == "12,50"
    assert celula(None) == ""
    assert celula(datetime(2026, 10, 30, 9, 5)) == "30/10/2026 09:05"
    assert celula(date(2026, 10, 30)) == "30/10/2026"
    assert celula(True) == "sim"
    assert celula(Decimal("-3.00")) == "-3,00"  # número negativo não é tratado como fórmula


def test_gerar_csv_tem_bom_separador_e_protecao():
    texto = gerar_csv([("placa", "Placa"), ("valor", "Valor"), ("cliente", "Cliente")],
                      [{"placa": "ABC1D23", "valor": Decimal("12"), "cliente": "=cmd()"}])
    assert texto.startswith("\ufeff")
    linhas = texto.lstrip("\ufeff").split("\r\n")
    assert linhas[0] == "Placa;Valor;Cliente"
    assert linhas[1] == "ABC1D23;12,00;'=cmd()"
