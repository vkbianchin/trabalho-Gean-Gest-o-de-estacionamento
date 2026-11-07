"""Redefinição de senha, 2FA, preferências e permissões das rotas novas."""
import contextlib
import json
import time

import pytest
from flask import session

from app import totp
from app.erros import ErroNegocio
from app.servicos import cancelamentos, manutencao, usuarios
from app.validadores import senha as validar_senha
from tests.test_manutencao_cancelamentos import BancoFalso, instalar

SEGREDO = "JBSWY3DPEHPK3PXP"
USUARIO = {"id": 1, "nome": "Ana", "login": "ana", "nivel_acesso": "operador", "trocar_senha": 0, "ativo": 1, "bloqueado_ate": None}


# ------------------------------------------------------------------ senha provisória
def test_senha_temporaria_sempre_cumpre_a_politica():
    vistas = set()
    for _ in range(200):
        s = usuarios.gerar_senha_temporaria()
        validar_senha(s)  # levanta ValueError se não cumprir (mínimo, letras e números)
        assert len(s) == 12 and not set(s) & set("0O1lI")
        vistas.add(s)
    assert len(vistas) == 200


def test_redefinir_senha_grava_hash_forca_troca_e_libera_bloqueio(monkeypatch):
    banco = instalar(monkeypatch, usuarios, BancoFalso({"id": 2, "ativo": 1}))
    monkeypatch.setattr(usuarios, "gerar_hash", lambda s: "HASH:" + s)
    r = usuarios.redefinir_senha_admin(2, admin_id=1)
    sql, params = banco.updates[0]
    assert "trocar_senha=1" in sql and "tentativas_login=0" in sql and "bloqueado_ate=NULL" in sql
    assert params[0] == "HASH:" + r["senha_provisoria"] and params[1:] == (1, 2)
    assert banco.auditoria[0][2] == "redefiniu senha"
    assert r["senha_provisoria"] not in json.dumps(banco.auditoria, default=str)  # a senha nunca vai para a auditoria


def test_redefinir_propria_senha_e_usuario_inexistente(monkeypatch):
    instalar(monkeypatch, usuarios, BancoFalso(None))
    with pytest.raises(ErroNegocio, match="própria"):
        usuarios.redefinir_senha_admin(1, admin_id=1)
    with pytest.raises(ErroNegocio) as e:
        usuarios.redefinir_senha_admin(5, admin_id=1)
    assert e.value.status == 404


def test_reativar_usuario(monkeypatch):
    banco = instalar(monkeypatch, usuarios, BancoFalso({"ativo": 0}))
    assert usuarios.reativar_usuario(2, admin_id=1)["mensagem"] == "Usuário reativado."
    assert "ativo=1" in banco.updates[0][0] and banco.auditoria[0][2] == "reativou"
    banco = instalar(monkeypatch, usuarios, BancoFalso({"ativo": 1}))
    assert "já está ativo" in usuarios.reativar_usuario(2, admin_id=1)["mensagem"]


# ------------------------------------------------------------------ login em duas etapas
@pytest.fixture()
def dois_fatores(app, monkeypatch):
    estado = {"tentativas": 0, "bloqueios": [], "zeradas": 0}
    monkeypatch.setattr(usuarios, "_ler_coluna", lambda uid, col: {"totp_segredo": SEGREDO, "totp_ativo": 1}.get(col))
    monkeypatch.setattr(usuarios, "conexao", lambda: BancoFalso(dict(USUARIO)))
    monkeypatch.setattr(usuarios, "_reservar_tentativa", lambda uid: estado.__setitem__("tentativas", estado["tentativas"] + 1) or estado["tentativas"])
    monkeypatch.setattr(usuarios, "_bloquear", lambda uid, ate: estado["bloqueios"].append(ate))
    monkeypatch.setattr(usuarios, "_zerar_tentativas", lambda uid: estado.__setitem__("zeradas", estado["zeradas"] + 1))
    return app, estado


def abrir_pre2fa(expira_em=300):
    session["pre2fa"] = {"uid": 1, "expira": time.time() + expira_em}


def test_codigo_correto_abre_a_sessao(dois_fatores):
    app, estado = dois_fatores
    with app.test_request_context():
        abrir_pre2fa()
        r = usuarios.login_segundo_fator(totp.codigo_em(SEGREDO))
        assert r["login"] == "ana" and session["usuario_id"] == 1 and "pre2fa" not in session
    assert estado["zeradas"] == 1


def test_codigo_errado_nao_abre_a_sessao(dois_fatores):
    app, _ = dois_fatores
    with app.test_request_context():
        abrir_pre2fa()
        with pytest.raises(ErroNegocio) as e:
            usuarios.login_segundo_fator("000000")
        assert e.value.status == 401 and "usuario_id" not in session


def test_cinco_codigos_errados_bloqueiam_a_conta(dois_fatores):
    app, estado = dois_fatores
    with app.test_request_context():
        abrir_pre2fa()
        for _ in range(4):
            with pytest.raises(ErroNegocio) as e:
                usuarios.login_segundo_fator("111111")
            assert e.value.status == 401
        with pytest.raises(ErroNegocio) as e:
            usuarios.login_segundo_fator("111111")
        assert e.value.status == 429 and len(estado["bloqueios"]) == 1 and "pre2fa" not in session


def test_segundo_fator_sem_senha_previa_ou_expirado(dois_fatores):
    app, _ = dois_fatores
    with app.test_request_context():
        with pytest.raises(ErroNegocio) as e:
            usuarios.login_segundo_fator(totp.codigo_em(SEGREDO))
        assert e.value.status == 401
        abrir_pre2fa(expira_em=-1)
        with pytest.raises(ErroNegocio, match="expirou"):
            usuarios.login_segundo_fator(totp.codigo_em(SEGREDO))


def test_login_com_senha_certa_mas_2fa_ativo_nao_abre_sessao(app, monkeypatch):
    from tests.test_bloqueio_login import BancoFalso as BancoLogin, AGORA
    banco = BancoLogin()
    monkeypatch.setattr(usuarios, "conexao", lambda: banco)
    monkeypatch.setattr(usuarios, "transacao", lambda: contextlib.nullcontext())
    monkeypatch.setattr(usuarios, "agora", lambda: AGORA)
    monkeypatch.setattr(usuarios, "verificar_hash", lambda s, h: s == h)
    monkeypatch.setattr(usuarios, "_ler_coluna", lambda uid, col: 1 if col == "totp_ativo" else None)
    usuarios._desconhecidos.clear()
    with app.test_request_context():
        assert usuarios.login("ana", "Senha123") == {"exige_2fa": True}
        assert "usuario_id" not in session and session["pre2fa"]["uid"] == 1


# ------------------------------------------------------------------ configurar 2FA
def test_ativar_2fa_exige_codigo_valido_do_segredo_novo(app, monkeypatch):
    banco = instalar(monkeypatch, usuarios, BancoFalso())
    monkeypatch.setattr(usuarios, "_ler_coluna", lambda uid, col: 0)
    with app.test_request_context():
        dados = usuarios.iniciar_2fa(1, "ana")
        assert dados["uri"].startswith("otpauth://totp/") and len(dados["segredo"]) == 32
        with pytest.raises(ErroNegocio):
            usuarios.confirmar_2fa(1, "000000")
        usuarios.confirmar_2fa(1, totp.codigo_em(dados["segredo"]))
        sql, params = banco.updates[0]
        assert "totp_ativo=1" in sql and params[0] == dados["segredo"]
        assert "totp_pendente" not in session and banco.auditoria[0][2] == "ativou 2fa"


def test_confirmar_sem_iniciar_e_ativar_duas_vezes(app, monkeypatch):
    instalar(monkeypatch, usuarios, BancoFalso())
    with app.test_request_context():
        monkeypatch.setattr(usuarios, "_ler_coluna", lambda uid, col: 0)
        with pytest.raises(ErroNegocio, match="Inicie"):
            usuarios.confirmar_2fa(1, "123456")
        monkeypatch.setattr(usuarios, "_ler_coluna", lambda uid, col: 1)
        with pytest.raises(ErroNegocio, match="já está ativa"):
            usuarios.iniciar_2fa(1, "ana")


def test_desativar_2fa_pede_senha_e_codigo(monkeypatch):
    banco = instalar(monkeypatch, usuarios, BancoFalso({"senha_hash": "h"}))
    monkeypatch.setattr(usuarios, "verificar_hash", lambda s, h: s == "certa")
    monkeypatch.setattr(usuarios, "_ler_coluna", lambda uid, col: SEGREDO)
    with pytest.raises(ErroNegocio, match="Senha"):
        usuarios.desativar_2fa(1, "errada", totp.codigo_em(SEGREDO))
    banco.respostas.append({"senha_hash": "h"})
    with pytest.raises(ErroNegocio, match="Código"):
        usuarios.desativar_2fa(1, "certa", "000000")
    banco.respostas.append({"senha_hash": "h"})
    usuarios.desativar_2fa(1, "certa", totp.codigo_em(SEGREDO))
    assert "totp_ativo=0" in banco.updates[0][0] and banco.auditoria[0][2] == "desativou 2fa"


# ------------------------------------------------------------------ preferências
def test_preferencias_sao_gravadas_no_banco_e_na_sessao(app, monkeypatch):
    banco = instalar(monkeypatch, usuarios, BancoFalso())
    prefs = {"tema": "claro", "tamanho_texto": "normal", "cor_destaque": "verde", "sons": "ligados"}
    with app.test_request_context():
        assert usuarios.salvar_preferencias(1, prefs) is True
        assert session["preferencias"] == prefs
    assert json.loads(banco.updates[0][1][0]) == prefs


def test_preferencias_sem_a_migracao_ficam_so_na_sessao(app, monkeypatch):
    from mysql.connector.errors import ProgrammingError

    class BancoSemColuna(BancoFalso):
        def cursor(self, **_):
            cur = super().cursor()
            cur.execute = lambda *a, **k: (_ for _ in ()).throw(ProgrammingError(msg="Unknown column", errno=1054))
            return cur
    instalar(monkeypatch, usuarios, BancoSemColuna())
    with app.test_request_context():
        assert usuarios.salvar_preferencias(1, {"tema": "claro"}) is False
        assert session["preferencias"] == {"tema": "claro"}


# ------------------------------------------------------------------ permissões das rotas novas
def logar(client, nivel):
    client.application.config["WTF_CSRF_ENABLED"] = False
    with client.session_transaction() as sessao:
        sessao.update({"usuario_id": 1, "nome": "T", "login": "t", "nivel_acesso": nivel, "trocar_senha": False})


SO_ADMIN = [("post", "/api/clientes/1/ativo"), ("post", "/api/veiculos/1/ativo"), ("put", "/api/vagas/1"), ("post", "/api/vagas/1/ativo"),
            ("post", "/api/movimentacoes/1/cancelar"), ("post", "/api/pagamentos/1/cancelar"),
            ("post", "/api/usuarios/2/redefinir-senha"), ("post", "/api/usuarios/2/ativar")]


@pytest.mark.parametrize("metodo,rota", SO_ADMIN)
def test_operador_nao_executa_acoes_de_administrador(client, metodo, rota):
    logar(client, "operador")
    assert getattr(client, metodo)(rota, json={"ativo": False, "motivo": "teste de permissão"}).status_code == 403


@pytest.mark.parametrize("metodo,rota", SO_ADMIN)
def test_sem_login_as_acoes_novas_devolvem_401(client, metodo, rota):
    client.application.config["WTF_CSRF_ENABLED"] = False
    assert getattr(client, metodo)(rota, json={}).status_code == 401


def test_operador_pode_editar_cliente_e_veiculo(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr(manutencao, "editar_cliente", lambda cid, d, uid: chamadas.append(("cliente", cid)) or {"mensagem": "ok"})
    monkeypatch.setattr(manutencao, "editar_veiculo", lambda vid, d, uid: chamadas.append(("veiculo", vid)) or {"mensagem": "ok"})
    logar(client, "operador")
    assert client.put("/api/clientes/4", json={}).status_code == 200
    assert client.put("/api/veiculos/6", json={}).status_code == 200
    assert chamadas == [("cliente", 4), ("veiculo", 6)]


def test_administrador_repassa_motivo_e_situacao(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(cancelamentos, "cancelar_pagamento", lambda pid, motivo, uid: capturado.update(pid=pid, motivo=motivo) or {"mensagem": "ok"})
    monkeypatch.setattr(manutencao, "alterar_situacao_vaga", lambda vid, ativo, uid: capturado.update(vaga=vid, ativo=ativo) or {"mensagem": "ok"})
    monkeypatch.setattr(usuarios, "redefinir_senha_admin", lambda alvo, admin: {"senha_provisoria": "Abc12345xyz9"})
    import app.rotas.administracao as adm
    monkeypatch.setattr(adm, "redefinir_senha_admin", usuarios.redefinir_senha_admin)
    logar(client, "administrador")
    assert client.post("/api/pagamentos/9/cancelar", json={"motivo": "Cobrança em duplicidade"}).status_code == 200
    assert client.post("/api/vagas/3/ativo", json={"ativo": False}).status_code == 200
    assert capturado == {"pid": 9, "motivo": "Cobrança em duplicidade", "vaga": 3, "ativo": False}
    assert client.post("/api/usuarios/2/redefinir-senha", json={}).get_json()["senha_provisoria"] == "Abc12345xyz9"


def test_pagina_de_seguranca_exige_login_mas_nao_perfil_de_administrador(client):
    assert client.get("/seguranca").status_code == 302
    logar(client, "operador")
    assert client.get("/seguranca").status_code == 200
