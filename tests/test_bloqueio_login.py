import contextlib
from datetime import datetime, timedelta

import pytest
from app.erros import ErroNegocio
from app.servicos import usuarios

AGORA = datetime(2026, 10, 26, 12, 0, 0)


class BancoFalso:
    """Simula só o necessário da tabela usuarios (sem MySQL) para testar a política de bloqueio."""
    def __init__(self):
        self.usuario = {"id": 1, "nome": "Ana", "login": "ana", "senha_hash": "Senha123", "nivel_acesso": "operador",
                        "trocar_senha": 0, "ativo": 1, "tentativas_login": 0, "bloqueado_ate": None}
        self.updates = []

    def cursor(self, dictionary=False):
        return CursorFalso(self)

    def commit(self): pass
    def rollback(self): pass


class CursorFalso:
    def __init__(self, banco):
        self.banco = banco
        self.resultado = None

    def execute(self, sql, params=()):
        sql = " ".join(sql.split())
        u = self.banco.usuario
        if sql.startswith("SELECT id, nome, login"):
            self.resultado = dict(u) if params[0] == u["login"] else None
        elif sql.startswith("UPDATE usuarios SET tentativas_login = tentativas_login + 1"):
            u["tentativas_login"] += 1
            self.banco.updates.append(sql)
        elif sql.startswith("SELECT tentativas_login FROM usuarios"):
            self.resultado = {"tentativas_login": u["tentativas_login"]}
        elif sql.startswith("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=NULL"):
            u["tentativas_login"], u["bloqueado_ate"] = 0, None
            self.banco.updates.append(sql)
        elif sql.startswith("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=%s"):
            u["tentativas_login"], u["bloqueado_ate"] = 0, params[0]
            self.banco.updates.append(sql)
        else:
            raise AssertionError(f"SQL inesperado: {sql}")

    def fetchone(self): return self.resultado
    def close(self): pass


@pytest.fixture()
def ambiente(app, monkeypatch):
    banco = BancoFalso()
    relogio = {"agora": AGORA}
    conferencias = {"senhas": 0}

    def verificar(senha, hash_guardado):
        conferencias["senhas"] += 1
        return senha == hash_guardado

    monkeypatch.setattr(usuarios, "conexao", lambda: banco)
    monkeypatch.setattr(usuarios, "transacao", lambda: contextlib.nullcontext())
    monkeypatch.setattr(usuarios, "agora", lambda: relogio["agora"])
    monkeypatch.setattr(usuarios, "verificar_hash", verificar)
    usuarios._desconhecidos.clear()
    return {"app": app, "banco": banco, "relogio": relogio, "conferencias": conferencias}


def tentar(ambiente, login, senha):
    with ambiente["app"].test_request_context():
        return usuarios.login(login, senha)


def falhar(ambiente, login="ana", senha="errada"):
    with pytest.raises(ErroNegocio) as erro:
        tentar(ambiente, login, senha)
    return erro.value


def test_quatro_falhas_ainda_nao_bloqueiam(ambiente):
    for _ in range(4):
        assert falhar(ambiente).status == 401
    assert tentar(ambiente, "ana", "Senha123")["login"] == "ana"


def test_quinta_falha_bloqueia_por_15_minutos(ambiente):
    for _ in range(4):
        falhar(ambiente)
    erro = falhar(ambiente)
    assert erro.status == 429 and "15 minuto" in erro.mensagem
    assert ambiente["banco"].usuario["bloqueado_ate"] == AGORA + timedelta(minutes=15)


def test_durante_o_bloqueio_nem_a_senha_certa_entra(ambiente):
    for _ in range(5):
        with pytest.raises(ErroNegocio):
            tentar(ambiente, "ana", "errada")
    conferidas = ambiente["conferencias"]["senhas"]
    ambiente["relogio"]["agora"] = AGORA + timedelta(minutes=10)
    erro = falhar(ambiente, senha="Senha123")
    assert erro.status == 429 and "5 minuto" in erro.mensagem
    assert ambiente["conferencias"]["senhas"] == conferidas  # a senha nem foi conferida


def test_bloqueio_expira_sozinho_e_libera_o_acesso(ambiente):
    for _ in range(5):
        with pytest.raises(ErroNegocio):
            tentar(ambiente, "ana", "errada")
    ambiente["relogio"]["agora"] = AGORA + timedelta(minutes=15, seconds=1)
    assert tentar(ambiente, "ana", "Senha123")["login"] == "ana"
    assert ambiente["banco"].usuario["tentativas_login"] == 0
    assert ambiente["banco"].usuario["bloqueado_ate"] is None


def test_apos_expirar_a_contagem_recomeca(ambiente):
    for _ in range(5):
        with pytest.raises(ErroNegocio):
            tentar(ambiente, "ana", "errada")
    ambiente["relogio"]["agora"] = AGORA + timedelta(minutes=16)
    for _ in range(4):
        assert falhar(ambiente).status == 401
    assert falhar(ambiente).status == 429


def test_login_correto_zera_a_contagem(ambiente):
    for _ in range(3):
        falhar(ambiente)
    tentar(ambiente, "ana", "Senha123")
    for _ in range(4):
        assert falhar(ambiente).status == 401


def test_tentativas_acima_do_limite_sao_negadas_sem_conferir_a_senha(ambiente):
    ambiente["banco"].usuario["tentativas_login"] = 5  # simula tentativas simultâneas já contadas
    erro = falhar(ambiente, senha="Senha123")
    assert erro.status == 429
    assert ambiente["conferencias"]["senhas"] == 0


def test_login_inexistente_tambem_e_limitado_com_a_mesma_resposta(ambiente):
    for _ in range(4):
        assert falhar(ambiente, login="fantasma").status == 401
    erro = falhar(ambiente, login="fantasma")
    assert erro.status == 429 and "15 minuto" in erro.mensagem
    assert falhar(ambiente, login="fantasma").status == 429


def test_contador_nao_altera_a_data_de_atualizacao_do_usuario(ambiente):
    falhar(ambiente)
    tentar(ambiente, "ana", "Senha123")
    assert ambiente["banco"].updates
    assert all("atualizado_em = atualizado_em" in sql for sql in ambiente["banco"].updates)


def test_minutos_restantes_arredonda_para_cima():
    assert usuarios.minutos_restantes(AGORA + timedelta(minutes=14, seconds=1), AGORA) == 15
    assert usuarios.minutos_restantes(AGORA + timedelta(seconds=30), AGORA) == 1
