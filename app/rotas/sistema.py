from flask import Blueprint, jsonify, request
from flask_wtf.csrf import generate_csrf

from ..db import conexao
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import configuracoes, sistema

bp = Blueprint("sistema", __name__)


@bp.get("/api/csrf")
def csrf():
    return jsonify({"csrf_token": generate_csrf()})


@bp.get("/saude")
def saude():
    """Verificação simples para monitoramento: o processo responde e o banco está acessível."""
    try:
        cur = conexao().cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        banco = True
    except Exception:
        banco = False
    return jsonify({"status": "ok" if banco else "degradado", "banco": banco}), 200 if banco else 503


@bp.get("/api/status")
@exigir("operacao")
def status():
    return jsonify(sistema.status_sistema())


@bp.get("/api/configuracoes")
@exigir("configuracoes")
def obter_configuracoes():
    return jsonify(configuracoes.obter())


@bp.put("/api/configuracoes")
@exigir("configuracoes")
def atualizar_configuracoes():
    return jsonify(configuracoes.atualizar(request.get_json(force=True), exigir_login()))
