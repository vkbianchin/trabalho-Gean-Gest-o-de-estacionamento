from datetime import datetime, timedelta
from decimal import Decimal
from app.cobranca import calcular_cobranca

def test_tolerancia_nao_cobra():
    inicio=datetime(2026,1,1,8,0); assert calcular_cobranca(inicio,inicio+timedelta(minutes=10),Decimal("6"))==Decimal("0.00")

def test_tolerancia_descontada_uma_vez():
    inicio=datetime(2026,1,1,8,0)
    assert calcular_cobranca(inicio,inicio+timedelta(minutes=65),Decimal("6"),10,"hora_cheia")==Decimal("6.00")
    assert calcular_cobranca(inicio,inicio+timedelta(minutes=71),Decimal("6"),10,"hora_cheia")==Decimal("12.00")

def test_fracao_de_30_minutos():
    inicio=datetime(2026,1,1,8,0)
    assert calcular_cobranca(inicio,inicio+timedelta(minutes=41),Decimal("6"),10,"fracao",30)==Decimal("6.00")

def test_diaria_limita_valor():
    inicio=datetime(2026,1,1,8,0)
    assert calcular_cobranca(inicio,inicio+timedelta(hours=10),Decimal("6"),10,"fracao",30,Decimal("40"))==Decimal("40.00")
