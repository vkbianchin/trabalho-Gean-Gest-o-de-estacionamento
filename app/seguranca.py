import bcrypt
from flask import session
from .db import conexao
from .erros import ErroNegocio
from .validadores import senha as validar_senha

def gerar_hash(senha):
    try:
        validar_senha(senha)
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_hash(senha, senha_hash):
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError, AttributeError):
        return False

def usuario_id():
    return session.get("usuario_id")

def exigir_login():
    if not session.get("usuario_id"):
        raise ErroNegocio("Faça login para continuar.", 401)
    if session.get("trocar_senha") and not session.get("permitir_troca_senha"):
        raise ErroNegocio("Troque sua senha antes de continuar.", 403)
    return session["usuario_id"]


def buscar_situacao_usuario(uid):
    """Lê no banco se o usuário continua ativo e qual é o perfil atual dele."""
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute("SELECT ativo, nivel_acesso, trocar_senha FROM usuarios WHERE id=%s", (uid,))
        return cur.fetchone()
    finally:
        cur.close()


def revalidar_sessao():
    """Confere a sessão contra o banco a cada requisição.

    Sem isso, um usuário desativado (ou rebaixado de perfil) continuaria usando o sistema
    até o cookie expirar. Devolve False quando a sessão foi encerrada.
    """
    uid = session.get("usuario_id")
    if not uid:
        return True
    situacao = buscar_situacao_usuario(uid)
    if not situacao or not situacao["ativo"]:
        session.clear()
        return False
    session["nivel_acesso"] = situacao["nivel_acesso"]
    session["trocar_senha"] = bool(situacao["trocar_senha"])
    return True
