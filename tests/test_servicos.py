"""Regras de negócio novas, testadas sem banco (consultas trocadas por dados falsos)."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.erros import ErroNegocio
from app.servicos import cadastros, configuracoes, financeiro, movimentacoes, relatorios


def mov_horista(**extra):
    base = {"id": 10, "cobranca": "hora", "plano_nome": "Horista", "tipo_nome": "Carro", "vaga_numero": 3,
            "entrada_em": datetime(2026, 10, 30, 10, 0), "valor_hora": Decimal("12.00"), "valor_diaria": None,
            "tolerancia_minutos": 10, "arredondamento": "fracao", "fracao_minutos": 30}
    return {**base, **extra}


# ---- saída: tempo total e valor -------------------------------------------------
def test_calcular_saida_horista_traz_tempo_e_valor():
    r = movimentacoes.calcular_saida(mov_horista(), datetime(2026, 10, 30, 12, 35))
    assert r["minutos"] == 155 and r["tempo"] == "2h 35min"
    assert r["valor"] == Decimal("30.00") and r["mensalista"] is False  # 155 min - 10 de tolerância = 145 -> 5 frações de 30 min x R$ 6


def test_calcular_saida_dentro_da_tolerancia_nao_cobra():
    r = movimentacoes.calcular_saida(mov_horista(), datetime(2026, 10, 30, 10, 9))
    assert r["valor"] == Decimal("0.00") and r["tempo"] == "9min"


def test_calcular_saida_mensalista_nao_cobra():
    r = movimentacoes.calcular_saida(mov_horista(cobranca="mensal", valor_hora=None), datetime(2026, 10, 30, 18, 0))
    assert r["valor"] == Decimal("0.00") and r["mensalista"] is True


def test_calcular_saida_exige_preco_e_ordem_das_datas():
    with pytest.raises(ErroNegocio, match="preço"):
        movimentacoes.calcular_saida(mov_horista(valor_hora=None), datetime(2026, 10, 30, 12, 0))
    with pytest.raises(ErroNegocio, match="anterior"):
        movimentacoes.calcular_saida(mov_horista(), datetime(2026, 10, 30, 9, 0))


def test_previa_nao_grava_e_indica_se_ha_pagamento(monkeypatch):
    monkeypatch.setattr(movimentacoes, "conexao", lambda: None)
    monkeypatch.setattr(movimentacoes, "_buscar_aberta", lambda conn, p: mov_horista(placa=p))
    monkeypatch.setattr(movimentacoes, "agora", lambda: datetime(2026, 10, 30, 12, 35))
    r = movimentacoes.previa_saida("abc-1d23")
    assert r["placa"] == "ABC1D23" and r["tempo"] == "2h 35min" and r["valor"] == "30.00"
    assert r["exige_pagamento"] is True and r["vaga"] == 3 and r["tolerancia_minutos"] == 10


def test_previa_rejeita_placa_invalida():
    with pytest.raises(ErroNegocio, match="Placa"):
        movimentacoes.previa_saida("123")


# ---- histórico por veículo ------------------------------------------------------
def test_historico_calcula_totais_e_ignora_canceladas():
    linhas = [
        {"id": 3, "entrada_em": datetime(2026, 10, 30, 9, 0), "saida_em": None, "vaga_numero": 1, "plano_nome": "Horista", "tipo_nome": "Carro"},
        {"id": 2, "entrada_em": datetime(2026, 10, 20, 10, 0), "saida_em": datetime(2026, 10, 20, 12, 0), "valor_cobrado": Decimal("20.00"),
         "vaga_numero": 1, "plano_nome": "Horista", "tipo_nome": "Carro", "operador": "Ana"},
        {"id": 1, "entrada_em": datetime(2026, 10, 10, 10, 0), "saida_em": datetime(2026, 10, 10, 11, 0), "valor_cobrado": Decimal("10.00"),
         "vaga_numero": 2, "plano_nome": "Horista", "tipo_nome": "Carro", "cancelada": 1},
    ]
    h = movimentacoes.montar_historico("ABC1D23", linhas)
    t = h["totais"]
    assert t["visitas"] == 2 and t["no_local"] == 1 and t["total_gasto"] == "20.00"
    assert t["tempo_total"] == "2h" and t["tempo_medio"] == "2h"
    assert h["passagens"][0]["no_local"] is True and h["passagens"][2]["cancelada"] is True
    assert t["primeira_visita"] == datetime(2026, 10, 20, 10, 0)


def test_historico_vazio():
    t = movimentacoes.montar_historico("ABC1D23", [])["totais"]
    assert t["visitas"] == 0 and t["total_gasto"] == "0.00" and t["tempo_medio"] is None and t["ultima_visita"] is None


# ---- relatórios ------------------------------------------------------------------
def test_ocupacao_completa_horas_e_dias_sem_entradas():
    r = relatorios.distribuir([{"chave": 8, "entradas": 4}, {"chave": 18, "entradas": 9}], [{"chave": 2, "entradas": 13}])
    assert len(r["por_hora"]) == 24 and len(r["por_dia_semana"]) == 7
    assert r["hora_de_pico"] == "18h" and r["total_entradas"] == 13
    assert r["por_dia_semana"][1] == {"dia": 2, "rotulo": "Segunda", "entradas": 13}
    assert r["por_hora"][0]["entradas"] == 0


def test_ocupacao_sem_dados_nao_tem_pico():
    assert relatorios.distribuir([], [])["hora_de_pico"] is None


# ---- financeiro ------------------------------------------------------------------
def test_inadimplencia_respeita_a_carencia(monkeypatch):
    abertas = [
        {"id": 1, "vencimento": date(2026, 10, 1), "valor": Decimal("300"), "cliente_nome": "Ana", "placa": "AAA1A11", "telefone": "1", "competencia": date(2026, 10, 1)},
        {"id": 2, "vencimento": date(2026, 10, 27), "valor": Decimal("300"), "cliente_nome": "Bia", "placa": "BBB2B22", "telefone": "2", "competencia": date(2026, 10, 1)},
        {"id": 3, "vencimento": date(2026, 11, 5), "valor": Decimal("300"), "cliente_nome": "Cai", "placa": "CCC3C33", "telefone": "3", "competencia": date(2026, 11, 1)},
    ]
    monkeypatch.setattr(financeiro, "_linhas", lambda *a, **k: [dict(x) for x in abertas])
    monkeypatch.setattr(financeiro.configuracoes, "carencia_atraso", lambda: 5)
    resultado = financeiro.inadimplencia(date(2026, 10, 30))
    assert [r["id"] for r in resultado] == [1]  # Bia está dentro da carência; Cai ainda não venceu
    assert resultado[0]["dias_atraso"] == 24 and resultado[0]["valor"] == "300.00"


# ---- configurações ---------------------------------------------------------------
DADOS_CONFIG = {"nome_estacionamento": "Central", "tolerancia_minutos": "10", "fracao_minutos": "30", "arredondamento": "fracao"}


def test_configuracoes_validas_incluem_dados_do_recibo():
    d = configuracoes.validar({**DADOS_CONFIG, "cnpj": "11.222.333/0001-81", "razao_social": "Central Ltda", "telefone": "(49) 99999-0000", "dias_carencia_atraso": 3})
    assert d["cnpj"] == "11222333000181" and d["telefone"] == "49999990000" and d["dias_carencia_atraso"] == 3 and d["tolerancia_minutos"] == 10


def test_configuracoes_campos_opcionais_podem_ficar_vazios():
    d = configuracoes.validar({**DADOS_CONFIG, "cnpj": "", "razao_social": "", "endereco": "", "telefone": ""})
    assert d["cnpj"] is None and d["razao_social"] is None and d["dias_carencia_atraso"] == 0


@pytest.mark.parametrize("alteracao", [
    {"arredondamento": "outra"}, {"fracao_minutos": 0}, {"fracao_minutos": 61}, {"tolerancia_minutos": -1},
    {"cnpj": "11.222.333/0001-82"}, {"dias_carencia_atraso": 31}, {"nome_estacionamento": "a@b"}, {"nome_estacionamento": ""},
])
def test_configuracoes_invalidas_sao_recusadas(alteracao):
    with pytest.raises(ValueError):
        configuracoes.validar({**DADOS_CONFIG, **alteracao})


# ---- cadastro de cliente (pessoa física / jurídica) ----------------------------------
class CursorFalso:
    def __init__(self):
        self.chamadas, self.lastrowid = [], 7
    def execute(self, sql, params=None): self.chamadas.append((sql, list(params or [])))
    def close(self): pass


class ConexaoFalsa:
    def __init__(self):
        self.cur, self.commits = CursorFalso(), 0
    def cursor(self, **_): return self.cur
    def commit(self): self.commits += 1
    def rollback(self): pass


BASE_CLIENTE = {"nome": "Maria Souza", "telefone": "(49) 99999-0000", "cep": "89560-000", "logradouro": "Rua das Flores",
                "numero": "10", "bairro": "Centro", "cidade": "Videira", "uf": "sc"}


@pytest.fixture()
def banco_falso(monkeypatch):
    conn, auditoria = ConexaoFalsa(), []
    monkeypatch.setattr(cadastros, "conexao", lambda: conn)
    monkeypatch.setattr(cadastros, "registrar_auditoria", lambda *a: auditoria.append(a))
    return conn, auditoria


def test_cliente_pessoa_fisica_grava_documento_e_audita(banco_falso):
    conn, auditoria = banco_falso
    novo_id = cadastros.criar_cliente({**BASE_CLIENTE, "documento": "529.982.247-25"}, uid=1)
    sql, params = conn.cur.chamadas[0]
    assert novo_id == 7 and "tipo_pessoa" in sql and "documento" in sql and "cpf" not in sql
    assert "52998224725" in params and "fisica" in params and "SC" in params
    assert conn.commits == 1 and auditoria[0][:3] == ("clientes", 7, "criou")


def test_cliente_antigo_com_campo_cpf_continua_funcionando(banco_falso):
    conn, _ = banco_falso
    cadastros.criar_cliente({**BASE_CLIENTE, "cpf": "52998224725"}, uid=1)
    assert "52998224725" in conn.cur.chamadas[0][1]


def test_cliente_pessoa_juridica_exige_cnpj_valido(banco_falso):
    conn, _ = banco_falso
    cadastros.criar_cliente({**BASE_CLIENTE, "nome": "Oficina Central Ltda", "tipo_pessoa": "juridica", "documento": "11.222.333/0001-81"}, uid=1)
    assert "11222333000181" in conn.cur.chamadas[0][1] and "juridica" in conn.cur.chamadas[0][1]
    with pytest.raises(ErroNegocio, match="CNPJ"):
        cadastros.criar_cliente({**BASE_CLIENTE, "tipo_pessoa": "juridica", "documento": "52998224725"}, uid=1)


@pytest.mark.parametrize("campo,valor", [("nome", "Maria@casa"), ("logradouro", "Rua @ 1"), ("bairro", "x@y"), ("cidade", "@Videira")])
def test_cliente_nao_aceita_arroba_fora_do_email(banco_falso, campo, valor):
    with pytest.raises(ErroNegocio, match="@"):
        cadastros.criar_cliente({**BASE_CLIENTE, "documento": "52998224725", campo: valor}, uid=1)


def test_cliente_aceita_arroba_no_email(banco_falso):
    cadastros.criar_cliente({**BASE_CLIENTE, "documento": "52998224725", "email": "maria@exemplo.com"}, uid=1)
