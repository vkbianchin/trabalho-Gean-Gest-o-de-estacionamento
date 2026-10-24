import bcrypt
from flask import session
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
