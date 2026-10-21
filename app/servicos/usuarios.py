from flask import session
from ..db import conexao
from ..seguranca import gerar_hash, verificar_hash
from ..erros import ErroNegocio
from ..validadores import senha as validar_senha, texto, email

_tentativas = {}

def login(login, senha):
    chave = (login or "").strip().lower()
    tentativas = _tentativas.get(chave, 0)
    if tentativas >= 5:
        raise ErroNegocio("Muitas tentativas. Peça ao administrador para verificar o acesso ou tente mais tarde.", 429)
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT id, nome, login, senha_hash, nivel_acesso, trocar_senha, ativo FROM usuarios WHERE login=%s OR email=%s LIMIT 1", (chave, chave))
    usuario = cur.fetchone()
    cur.close()
    if not usuario or not usuario["ativo"] or not verificar_hash(senha or "", usuario["senha_hash"]):
        _tentativas[chave] = tentativas + 1
        raise ErroNegocio("Login ou senha incorretos.", 401)
    _tentativas.pop(chave, None)
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
    nome = texto(nome, "nome", 2, 100)
    email_usuario = email(email_usuario, True)
    login_usuario = texto(login_usuario, "login", 3, 50).lower()
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
