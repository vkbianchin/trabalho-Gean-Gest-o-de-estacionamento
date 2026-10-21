import pytest
from app.validadores import placa, cpf, dinheiro, cep

def test_placa_normalizada(): assert placa("abc-1d23")=="ABC1D23"
def test_placa_invalida():
    with pytest.raises(ValueError): placa("123-ABCD")
def test_cpf_invalido():
    with pytest.raises(ValueError): cpf("11111111111")
def test_dinheiro_decimal(): assert str(dinheiro("12,50"))=="12.50"
def test_cep(): assert cep("89560-000")=="89560000"
