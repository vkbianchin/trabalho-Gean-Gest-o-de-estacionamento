from functools import wraps
from flask import session
from .erros import ErroNegocio
from .seguranca import exigir_login

PERMISSOES = {
    "operacao": {"administrador", "operador"},
    "cadastros": {"administrador", "operador"},
    "contratos": {"administrador"},
    "precos": {"administrador"},
    "configuracoes": {"administrador"},
    "cancelar": {"administrador"},
    "retroativa": {"administrador"},
    "usuarios": {"administrador"},
    "auditoria": {"administrador"},
}

def exigir(permissao):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            exigir_login()
            if session.get("nivel_acesso") not in PERMISSOES.get(permissao, set()):
                raise ErroNegocio("Você não tem permissão para esta ação.", 403)
            return func(*args, **kwargs)
        return wrapper
    return decorador
