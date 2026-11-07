from datetime import date, datetime
from decimal import Decimal

import pytest

from app import create_app
from app.config import Config


def logar(client, nivel="administrador", trocar_senha=False):
    with client.session_transaction() as sessao:
        sessao.update({"usuario_id": 1, "nome": "Teste", "login": "teste", "nivel_acesso": nivel, "trocar_senha": trocar_senha})


def test_respostas_trazem_cabecalhos_de_seguranca(client):
    r = client.get("/login")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    csp = r.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp


def test_paginas_e_apis_nao_ficam_em_cache(client):
    assert "no-store" in client.get("/login").headers["Cache-Control"]
    assert "no-store" in client.get("/api/csrf").headers["Cache-Control"]


def test_arquivos_estaticos_podem_usar_cache(client):
    r = client.get("/static/css/app.css")
    assert r.status_code == 200
    assert "no-store" not in r.headers.get("Cache-Control", "")


def test_login_nao_reaparece_para_quem_ja_esta_logado(client):
    assert client.get("/login").status_code == 200
    logar(client)
    r = client.get("/login")
    assert r.status_code == 302 and r.headers["Location"].endswith("/")


def test_login_leva_a_troca_de_senha_quando_obrigatoria(client):
    logar(client, trocar_senha=True)
    assert client.get("/login").headers["Location"].endswith("/trocar-senha")


def test_logout_encerra_a_sessao_e_o_voltar_pede_login(client):
    logar(client)
    assert client.get("/clientes").status_code == 200
    client.post("/api/logout", json={}, headers={"X-CSRFToken": client.get("/api/csrf").get_json()["csrf_token"]})
    r = client.get("/clientes")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_json_devolve_datas_em_iso_sem_fuso(app):
    texto = app.json.dumps({"d": datetime(2026, 10, 30, 10, 0), "dia": date(2026, 10, 30), "v": Decimal("1.50")})
    assert '"2026-10-30T10:00:00"' in texto and '"2026-10-30"' in texto and '"1.50"' in texto
    assert "GMT" not in texto


def test_saude_informa_quando_o_banco_responde(client, monkeypatch):
    class Cur:
        def execute(self, *_): pass
        def fetchone(self): return (1,)
        def close(self): pass
    class Conn:
        def cursor(self): return Cur()
    monkeypatch.setattr("app.rotas.sistema.conexao", lambda: Conn())
    r = client.get("/saude")
    assert r.status_code == 200 and r.get_json() == {"status": "ok", "banco": True}


def test_saude_devolve_503_quando_o_banco_cai(client, monkeypatch):
    def quebrar():
        raise RuntimeError("sem banco")
    monkeypatch.setattr("app.rotas.sistema.conexao", quebrar)
    r = client.get("/saude")
    assert r.status_code == 503 and r.get_json()["banco"] is False


class ConfigComRevalidacao(Config):
    TESTING = False
    SECRET_KEY = "chave-somente-para-testes"
    LOG_FILE = "logs/teste-revalidacao.log"


@pytest.fixture()
def cliente_revalidando(monkeypatch):
    monkeypatch.setattr("app.inicializar_pool", lambda _app: None)  # não tenta abrir conexão com o MySQL
    return create_app(ConfigComRevalidacao).test_client()


def test_usuario_desativado_perde_a_sessao_na_proxima_requisicao(cliente_revalidando, monkeypatch):
    monkeypatch.setattr("app.seguranca.buscar_situacao_usuario", lambda uid: {"ativo": 0, "nivel_acesso": "operador", "trocar_senha": 0})
    logar(cliente_revalidando, "operador")
    r = cliente_revalidando.get("/api/sessao")
    assert r.status_code == 401
    pagina = cliente_revalidando.get("/clientes")
    assert pagina.status_code == 302 and "/login" in pagina.headers["Location"]


def test_mudanca_de_perfil_vale_na_hora(cliente_revalidando, monkeypatch):
    monkeypatch.setattr("app.seguranca.buscar_situacao_usuario", lambda uid: {"ativo": 1, "nivel_acesso": "operador", "trocar_senha": 0})
    logar(cliente_revalidando, "administrador")  # o cookie ainda diz "administrador"
    assert cliente_revalidando.get("/api/sessao").get_json()["nivel_acesso"] == "operador"
    assert cliente_revalidando.get("/usuarios").status_code == 403  # perdeu o acesso de administrador
