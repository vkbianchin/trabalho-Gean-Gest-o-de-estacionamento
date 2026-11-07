import base64

import pytest

from app import totp

# Vetores de teste do RFC 6238 (SHA-1; segredo ASCII "12345678901234567890").
SEGREDO_RFC = base64.b32encode(b"12345678901234567890").decode()


@pytest.mark.parametrize("instante,esperado", [(59, "94287082"), (1111111109, "07081804"), (1111111111, "14050471"),
                                               (1234567890, "89005924"), (2000000000, "69279037")])
def test_codigos_do_rfc_6238(instante, esperado):
    assert totp.codigo_em(SEGREDO_RFC, instante, digitos=8) == esperado


def test_codigo_de_seis_digitos_e_os_ultimos_do_rfc():
    assert totp.codigo_em(SEGREDO_RFC, 59) == "287082"


def test_verificar_aceita_janela_de_um_passo_e_recusa_alem_dela():
    agora = 1_700_000_000
    codigo = totp.codigo_em(SEGREDO_RFC, agora)
    assert totp.verificar(SEGREDO_RFC, codigo, agora)
    assert totp.verificar(SEGREDO_RFC, codigo, agora + 30)       # relógio 30 s adiantado
    assert totp.verificar(SEGREDO_RFC, codigo, agora - 30)
    assert not totp.verificar(SEGREDO_RFC, codigo, agora + 120)  # fora da tolerância


@pytest.mark.parametrize("entrada", ["", None, "12345", "abcdef", "1234567", "000000"])
def test_verificar_recusa_formatos_invalidos_ou_errados(entrada):
    assert not totp.verificar(SEGREDO_RFC, entrada, 1_700_000_000)


def test_verificar_ignora_espacos_do_codigo():
    agora = 1_700_000_000
    c = totp.codigo_em(SEGREDO_RFC, agora)
    assert totp.verificar(SEGREDO_RFC, f"{c[:3]} {c[3:]}", agora)


def test_segredo_gerado_tem_tamanho_e_alfabeto_base32_e_nao_repete():
    a, b = totp.gerar_segredo(), totp.gerar_segredo()
    assert len(a) == 32 and set(a) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567") and a != b
    assert len(totp.codigo_em(a)) == 6


def test_uri_de_provisionamento():
    uri = totp.uri_provisionamento("ABC234", "ana@x", "ParkFlow")
    assert uri.startswith("otpauth://totp/ParkFlow:ana%40x?secret=ABC234") and "issuer=ParkFlow" in uri and "period=30" in uri
