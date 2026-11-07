import pytest

from app.validadores import (cnpj, documento, documento_livre, formatar_documento, intervalo_iso, texto, tipo_pessoa)

CPF_VALIDO = "529.982.247-25"
CNPJ_VALIDO = "11.222.333/0001-81"


def test_cnpj_valido_devolve_so_digitos():
    assert cnpj(CNPJ_VALIDO) == "11222333000181"


@pytest.mark.parametrize("valor", ["11.222.333/0001-82", "00000000000000", "123", "", None, "11222333000"])
def test_cnpj_invalido_e_recusado(valor):
    with pytest.raises(ValueError):
        cnpj(valor)


def test_documento_segue_o_tipo_de_pessoa():
    assert documento("fisica", CPF_VALIDO) == "52998224725"
    assert documento("juridica", CNPJ_VALIDO) == "11222333000181"
    with pytest.raises(ValueError):
        documento("fisica", CNPJ_VALIDO)  # CNPJ não vale como CPF
    with pytest.raises(ValueError):
        documento("juridica", CPF_VALIDO)  # CPF não vale como CNPJ


def test_documento_livre_descobre_pelo_tamanho():
    assert documento_livre(CPF_VALIDO) == "52998224725"
    assert documento_livre(CNPJ_VALIDO) == "11222333000181"
    with pytest.raises(ValueError):
        documento_livre("12345")


def test_formatar_documento():
    assert formatar_documento("52998224725") == CPF_VALIDO
    assert formatar_documento("11222333000181") == CNPJ_VALIDO
    assert formatar_documento("") == ""


def test_tipo_pessoa_padrao_e_invalido():
    assert tipo_pessoa(None) == "fisica"
    assert tipo_pessoa("JURIDICA") == "juridica"
    with pytest.raises(ValueError):
        tipo_pessoa("outro")


def test_arroba_so_e_aceito_quando_autorizado():
    with pytest.raises(ValueError, match="@"):
        texto("maria@casa", "nome")
    assert texto("maria@casa", "nome", permitir_arroba=True) == "maria@casa"
    assert texto("  Maria  ", "nome") == "Maria"


def test_intervalo_iso():
    ini, fim = intervalo_iso("2026-10-01", "2026-10-31")
    assert (fim - ini).days == 30
    with pytest.raises(ValueError):
        intervalo_iso("2026-10-31", "2026-10-01")
    with pytest.raises(ValueError):
        intervalo_iso("31/10/2026", "2026-10-31")
    with pytest.raises(ValueError):
        intervalo_iso("2020-01-01", "2026-01-01")  # período longo demais
