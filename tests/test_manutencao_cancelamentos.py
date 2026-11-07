"""Edição, desativação, cancelamento e estorno — testados com um banco falso que devolve respostas em sequência."""
import contextlib
from datetime import datetime
from decimal import Decimal

import pytest
from mysql.connector.errors import IntegrityError

from app.erros import ErroNegocio
from app.servicos import cancelamentos, manutencao


class CursorFalso:
    def __init__(self, banco):
        self.banco = banco

    def execute(self, sql, params=()):
        self.banco.sqls.append((" ".join(sql.split()), tuple(params or ())))
        if self.banco.falha_em and self.banco.falha_em in sql:
            raise IntegrityError(msg="duplicado", errno=1062)

    def fetchone(self):
        return self.banco.respostas.pop(0) if self.banco.respostas else None

    def close(self):
        pass


class BancoFalso:
    def __init__(self, *respostas, falha_em=None):
        self.respostas, self.sqls, self.falha_em, self.auditoria = list(respostas), [], falha_em, []

    def cursor(self, **_):
        return CursorFalso(self)

    def commit(self):
        pass

    def rollback(self):
        pass

    @property
    def updates(self):
        return [s for s in self.sqls if s[0].startswith("UPDATE")]


def instalar(monkeypatch, modulo, banco):
    monkeypatch.setattr(modulo, "conexao", lambda: banco)
    monkeypatch.setattr(modulo, "transacao", lambda: contextlib.nullcontext())
    monkeypatch.setattr(modulo, "registrar_auditoria", lambda *a: banco.auditoria.append(a))
    return banco


CLIENTE = {"id": 1, "nome": "Maria Souza", "tipo_pessoa": "fisica", "documento": "52998224725", "telefone": "49999990000", "email": None,
           "cep": "89560000", "logradouro": "Rua A", "numero": "10", "complemento": None, "bairro": "Centro", "cidade": "Videira", "uf": "SC", "ativo": 1}
FORM_CLIENTE = {"nome": "Maria Souza", "telefone": "(49) 99999-0000", "cep": "89560-000", "logradouro": "Rua A", "numero": "10",
                "bairro": "Centro", "cidade": "Videira", "uf": "SC"}


# ------------------------------------------------------------------ clientes
def test_editar_cliente_grava_so_o_que_mudou_e_nao_toca_no_documento(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(CLIENTE))
    manutencao.editar_cliente(1, {**FORM_CLIENTE, "telefone": "(49) 98888-7777", "cidade": "Joaçaba"}, uid=9)
    sql, params = banco.updates[0]
    assert "telefone=%s" in sql and "cidade=%s" in sql and "nome=%s" not in sql and "documento" not in sql
    assert params == ("49988887777", "Joaçaba", 1)
    acao = banco.auditoria[0]
    assert acao[:3] == ("clientes", 1, "alterou") and acao[4] == {"telefone": "49999990000", "cidade": "Videira"}


def test_editar_cliente_sem_mudanca_nao_grava(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(CLIENTE))
    assert "Nenhuma" in manutencao.editar_cliente(1, FORM_CLIENTE, uid=9)["mensagem"]
    assert not banco.updates and not banco.auditoria


def test_editar_cliente_valida_dados_e_arroba(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(CLIENTE))
    with pytest.raises(ErroNegocio, match="@"):
        manutencao.editar_cliente(1, {**FORM_CLIENTE, "nome": "Maria@x"}, uid=9)


def test_cliente_inexistente(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(None))
    with pytest.raises(ErroNegocio) as e:
        manutencao.editar_cliente(99, FORM_CLIENTE, uid=9)
    assert e.value.status == 404


def test_desativar_cliente_com_contrato_vigente_e_bloqueado(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(CLIENTE, {"id": 5}))
    with pytest.raises(ErroNegocio, match="contrato"):
        manutencao.alterar_situacao_cliente(1, False, uid=9)
    assert not banco.updates


def test_desativar_cliente_sem_contrato(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(CLIENTE, None))
    assert manutencao.alterar_situacao_cliente(1, False, uid=9)["mensagem"] == "Cliente desativado."
    assert banco.updates[0] == ("UPDATE clientes SET ativo=%s WHERE id=%s", (0, 1))
    assert banco.auditoria[0][2] == "desativou"


# ------------------------------------------------------------------ veículos
VEICULO = {"id": 3, "placa": "ABC1D23", "cliente_id": 1, "tipo_veiculo_id": 1, "modelo_id": None, "cor_id": None, "ativo": 1, "cliente_ativo": 1}


def test_desativar_veiculo_estacionado_e_bloqueado(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VEICULO, None, {"id": 10}))  # sem contrato, mas com entrada aberta
    with pytest.raises(ErroNegocio, match="estacionado"):
        manutencao.alterar_situacao_veiculo(3, False, uid=9)


def test_ativar_veiculo_de_cliente_inativo_e_bloqueado(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso({**VEICULO, "ativo": 0, "cliente_ativo": 0}))
    with pytest.raises(ErroNegocio, match="cliente"):
        manutencao.alterar_situacao_veiculo(3, True, uid=9)


def test_editar_veiculo_recusa_modelo_de_outro_tipo(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VEICULO, {"tipo_veiculo_id": 2}))
    with pytest.raises(ErroNegocio, match="compatível"):
        manutencao.editar_veiculo(3, {"modelo_id": 7}, uid=9)


def test_editar_veiculo_grava_modelo_e_cor(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(VEICULO, {"tipo_veiculo_id": 1}, {"id": 4}))
    manutencao.editar_veiculo(3, {"modelo_id": 7, "cor_id": 4}, uid=9)
    assert banco.updates[0][1] == (7, 4, 3) and "placa" not in banco.updates[0][0]


# ------------------------------------------------------------------ vagas
VAGA = {"id": 2, "numero": 2, "tipo_veiculo_id": 1, "plano_id": 1, "ativo": 1, "cobranca": "hora", "plano_ativo": 1}
VAGA_MENSAL = {**VAGA, "plano_id": 2, "cobranca": "mensal"}


def test_desativar_vaga_ocupada_e_bloqueado(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VAGA, {"id": 10}))
    with pytest.raises(ErroNegocio, match="ocupada"):
        manutencao.alterar_situacao_vaga(2, False, uid=9)


def test_desativar_vaga_livre(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(VAGA, None))
    assert manutencao.alterar_situacao_vaga(2, False, uid=9)["mensagem"] == "Vaga desativada."
    assert banco.updates[0][1] == (0, 2)


def test_desativar_vaga_mensal_de_que_contratos_dependem_e_bloqueado(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VAGA_MENSAL, None, {"n": 3}, {"n": 2}))  # 3 contratos, só 2 vagas restariam
    with pytest.raises(ErroNegocio, match="contratos"):
        manutencao.alterar_situacao_vaga(2, False, uid=9)


def test_desativar_vaga_mensal_com_folga(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(VAGA_MENSAL, None, {"n": 1}, {"n": 2}))
    manutencao.alterar_situacao_vaga(2, False, uid=9)
    assert banco.updates


def test_trocar_plano_de_vaga_ocupada_e_bloqueado(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VAGA, {"id": 10}))
    with pytest.raises(ErroNegocio, match="ocupada"):
        manutencao.editar_vaga(2, {"plano_id": 2}, uid=9)


def test_renumerar_vaga_ocupada_e_permitido(monkeypatch):
    banco = instalar(monkeypatch, manutencao, BancoFalso(VAGA))
    manutencao.editar_vaga(2, {"numero": 20}, uid=9)
    assert banco.updates[0] == ("UPDATE vagas SET numero=%s WHERE id=%s", (20, 2))


def test_numero_de_vaga_repetido_devolve_409(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VAGA, falha_em="UPDATE vagas"))
    with pytest.raises(ErroNegocio) as e:
        manutencao.editar_vaga(2, {"numero": 5}, uid=9)
    assert e.value.status == 409


def test_vaga_numero_fora_da_faixa(monkeypatch):
    instalar(monkeypatch, manutencao, BancoFalso(VAGA))
    with pytest.raises(ErroNegocio, match="entre 1 e 9999"):
        manutencao.editar_vaga(2, {"numero": 0}, uid=9)


# ------------------------------------------------------------------ cancelar movimentação
MOV_ABERTA = {"id": 10, "placa": "ABC1D23", "saida_em": None, "valor_cobrado": None, "cancelada": 0}


def test_cancelar_entrada_aberta_libera_a_vaga(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso(MOV_ABERTA, {"n": 0}))
    monkeypatch.setattr(cancelamentos, "agora", lambda: datetime(2026, 10, 30, 10, 0))
    assert cancelamentos.cancelar_movimentacao(10, "Placa digitada errada", uid=1)["mensagem"] == "Movimentação cancelada."
    sql, params = banco.updates[0]
    assert "cancelada=1" in sql and "saida_em=entrada_em" in sql and "valor_cobrado=0" in sql
    assert params[0] == 1 and params[2] == "Placa digitada errada" and params[-1] == 10
    assert banco.auditoria[0][2] == "cancelou"


def test_cancelar_passagem_encerrada_nao_mexe_na_saida(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso({**MOV_ABERTA, "saida_em": datetime(2026, 10, 30, 12, 0)}, {"n": 0}))
    cancelamentos.cancelar_movimentacao(10, "Lançamento duplicado", uid=1)
    assert "saida_em" not in banco.updates[0][0]


def test_cancelar_movimentacao_exige_motivo_util(monkeypatch):
    instalar(monkeypatch, cancelamentos, BancoFalso(MOV_ABERTA))
    for motivo in (None, "", "abc"):
        with pytest.raises(ErroNegocio):
            cancelamentos.cancelar_movimentacao(10, motivo, uid=1)


def test_cancelar_movimentacao_com_pagamento_recebido_e_bloqueado(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso({**MOV_ABERTA, "saida_em": datetime(2026, 10, 30, 12, 0)}, {"n": 1}))
    with pytest.raises(ErroNegocio, match="Estorne"):
        cancelamentos.cancelar_movimentacao(10, "Cliente desistiu", uid=1)
    assert not banco.updates


def test_cancelar_movimentacao_ja_cancelada(monkeypatch):
    instalar(monkeypatch, cancelamentos, BancoFalso({**MOV_ABERTA, "cancelada": 1}))
    with pytest.raises(ErroNegocio) as e:
        cancelamentos.cancelar_movimentacao(10, "Qualquer motivo", uid=1)
    assert e.value.status == 409


# ------------------------------------------------------------------ cancelar/estornar pagamento
def pagamento(**extra):
    return {"id": 7, "situacao": "pago", "valor": Decimal("30.00"), "contrato_id": None, "forma_pagamento": "pix", "caixa_id": 1, "fechado_em": None, **extra}


def test_estorno_de_pagamento_de_horista_cancela(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso(pagamento()))
    r = cancelamentos.cancelar_pagamento(7, "Cobrança duplicada", uid=1)
    assert r["situacao"] == "cancelado" and "situacao='cancelado'" in banco.updates[0][0]
    assert banco.auditoria[0][2] == "cancelou" and banco.auditoria[0][5]["situacao"] == "cancelado"


def test_estorno_de_mensalidade_paga_reabre_a_cobranca(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso(pagamento(contrato_id=4)))
    r = cancelamentos.cancelar_pagamento(7, "Pago na parcela errada", uid=1)
    sql = banco.updates[0][0]
    assert r["situacao"] == "aberto" and "situacao='aberto'" in sql and "caixa_id=NULL" in sql and "pago_em=NULL" in sql
    assert banco.auditoria[0][2] == "estornou"


def test_mensalidade_em_aberto_pode_ser_cancelada(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso(pagamento(situacao="aberto", caixa_id=None, contrato_id=4)))
    assert cancelamentos.cancelar_pagamento(7, "Contrato encerrado antes", uid=1)["situacao"] == "cancelado"
    assert banco.updates


def test_estorno_em_caixa_fechado_e_bloqueado(monkeypatch):
    banco = instalar(monkeypatch, cancelamentos, BancoFalso(pagamento(fechado_em=datetime(2026, 10, 29, 20, 0))))
    with pytest.raises(ErroNegocio, match="fechado"):
        cancelamentos.cancelar_pagamento(7, "Erro de digitação", uid=1)
    assert not banco.updates


def test_pagamento_ja_cancelado_e_inexistente(monkeypatch):
    instalar(monkeypatch, cancelamentos, BancoFalso(pagamento(situacao="cancelado")))
    with pytest.raises(ErroNegocio) as e:
        cancelamentos.cancelar_pagamento(7, "Qualquer motivo", uid=1)
    assert e.value.status == 409
    instalar(monkeypatch, cancelamentos, BancoFalso(None))
    with pytest.raises(ErroNegocio) as e:
        cancelamentos.cancelar_pagamento(99, "Qualquer motivo", uid=1)
    assert e.value.status == 404
