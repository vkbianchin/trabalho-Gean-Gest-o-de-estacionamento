from datetime import timedelta
from math import ceil
from flask import session, current_app
from ..db import conexao, transacao
from ..seguranca import gerar_hash, verificar_hash
from ..erros import ErroNegocio
from ..tempo import agora
from ..validadores import senha as validar_senha, texto, email

# Política de limitação de tentativas de login:
# 5 falhas seguidas bloqueiam a conta por 15 minutos; depois o bloqueio expira sozinho.
# A contagem fica no banco (usuarios.tentativas_login e usuarios.bloqueado_ate).
MAX_TENTATIVAS = 5
BLOQUEIO_MINUTOS = 15

# Logins que não existem também são limitados (só em memória), para que o bloqueio
# não revele quais logins existem no sistema.
_LIMITE_DESCONHECIDOS = 5000
_desconhecidos = {}

def bloqueado(bloqueado_ate, referencia):
    return bool(bloqueado_ate) and bloqueado_ate > referencia

def minutos_restantes(bloqueado_ate, referencia):
    return max(1, ceil((bloqueado_ate - referencia).total_seconds() / 60))

def _erro_bloqueio(bloqueado_ate=None, referencia=None):
    if bloqueado_ate and referencia:
        return ErroNegocio(f"Muitas tentativas. Tente novamente em {minutos_restantes(bloqueado_ate, referencia)} minuto(s).", 429)
    return ErroNegocio("Muitas tentativas. Aguarde alguns minutos e tente novamente.", 429)

def _desconhecido_bloqueado(chave, referencia):
    registro = _desconhecidos.get(chave)
    return registro["ate"] if registro and bloqueado(registro["ate"], referencia) else None

def _desconhecido_falhou(chave, referencia):
    """Conta a falha de um login inexistente; devolve o fim do bloqueio se ele foi acionado agora."""
    if len(_desconhecidos) >= _LIMITE_DESCONHECIDOS:
        _desconhecidos.clear()
    registro = _desconhecidos.setdefault(chave, {"falhas": 0, "ate": None})
    registro["falhas"] += 1
    if registro["falhas"] >= MAX_TENTATIVAS:
        registro["falhas"] = 0
        registro["ate"] = referencia + timedelta(minutes=BLOQUEIO_MINUTOS)
        return registro["ate"]
    return None

# "atualizado_em = atualizado_em" evita que o contador de login altere a data de atualização do usuário.
def _reservar_tentativa(uid):
    """Conta a tentativa ANTES de conferir a senha (operação atômica no banco), para que
    várias tentativas simultâneas não ultrapassem o limite."""
    conn = conexao()
    with transacao():
        cur = conn.cursor(dictionary=True)
        cur.execute("UPDATE usuarios SET tentativas_login = tentativas_login + 1, atualizado_em = atualizado_em WHERE id=%s", (uid,))
        cur.execute("SELECT tentativas_login FROM usuarios WHERE id=%s FOR UPDATE", (uid,))
        tentativas = int(cur.fetchone()["tentativas_login"])
        cur.close()
    return tentativas

def _bloquear(uid, ate):
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=%s, atualizado_em = atualizado_em WHERE id=%s", (ate, uid))
        cur.close()

def _zerar_tentativas(uid):
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=NULL, atualizado_em = atualizado_em WHERE id=%s", (uid,))
        cur.close()

def login(login, senha):
    chave = (login or "").strip().lower()[:150]
    referencia = agora()
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT id, nome, login, senha_hash, nivel_acesso, trocar_senha, ativo, bloqueado_ate FROM usuarios WHERE login=%s OR email=%s LIMIT 1", (chave, chave))
    usuario = cur.fetchone()
    cur.close()
    if not usuario:
        ate = _desconhecido_bloqueado(chave, referencia) or _desconhecido_falhou(chave, referencia)
        if ate:
            raise _erro_bloqueio(ate, referencia)
        raise ErroNegocio("Login ou senha incorretos.", 401)
    if bloqueado(usuario["bloqueado_ate"], referencia):
        raise _erro_bloqueio(usuario["bloqueado_ate"], referencia)
    tentativas = _reservar_tentativa(usuario["id"])
    if tentativas > MAX_TENTATIVAS:
        raise _erro_bloqueio()
    if not usuario["ativo"] or not verificar_hash(senha or "", usuario["senha_hash"]):
        if tentativas >= MAX_TENTATIVAS:
            ate = referencia + timedelta(minutes=BLOQUEIO_MINUTOS)
            _bloquear(usuario["id"], ate)
            current_app.logger.warning("Login bloqueado por excesso de tentativas: usuario_id=%s", usuario["id"])
            raise _erro_bloqueio(ate, referencia)
        raise ErroNegocio("Login ou senha incorretos.", 401)
    _zerar_tentativas(usuario["id"])
    _desconhecidos.pop(chave, None)
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario["id"]
    session["nome"] = usuario["nome"]
    session["login"] = usuario["login"]
    session["nivel_acesso"] = usuario["nivel_acesso"]
    session["trocar_senha"] = bool(usuario["trocar_senha"])
    session["permitir_troca_senha"] = False
    return {k: usuario[k] for k in ("id", "nome", "login", "nivel_acesso", "trocar_senha")}

def trocar_senha(usuario_id, atual, nova):
    validar_senha(nova)
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT senha_hash FROM usuarios WHERE id=%s AND ativo=1", (usuario_id,))
    usuario = cur.fetchone()
    cur.close()
    if not usuario or not verificar_hash(atual or "", usuario["senha_hash"]):
        raise ErroNegocio("A senha atual está incorreta.", 400)
    conn = conexao()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET senha_hash=%s, trocar_senha=0, atualizado_por=%s WHERE id=%s", (gerar_hash(nova), usuario_id, usuario_id))
    cur.close()
    conn.commit()
    session["trocar_senha"] = False
    session["permitir_troca_senha"] = False

def criar_usuario(nome, email_usuario, login_usuario, senha_inicial, nivel, criador_id, provisoria=False):
    try:
        nome = texto(nome, "nome", 2, 100)
        email_usuario = email(email_usuario, True)
        login_usuario = texto(login_usuario, "login", 3, 50).lower()
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    if nivel not in ("administrador", "operador"):
        raise ErroNegocio("Nível de acesso inválido.")
    hash_senha = gerar_hash(senha_inicial)
    conn = conexao()
    cur = conn.cursor()
    cur.execute("INSERT INTO usuarios (nome,email,login,senha_hash,nivel_acesso,trocar_senha,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s)", (nome,email_usuario,login_usuario,hash_senha,nivel,int(provisoria),criador_id))
    uid = cur.lastrowid
    conn.commit()
    cur.close()
    return uid
