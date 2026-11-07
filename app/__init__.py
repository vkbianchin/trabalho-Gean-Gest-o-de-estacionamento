import logging
import os
from datetime import date, datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, redirect, request, session
from flask.json.provider import DefaultJSONProvider
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .db import fechar_conexao, inicializar_pool
from .erros import ErroNegocio, registrar_erros
from .rotas import registrar_rotas
from .seguranca import revalidar_sessao

csrf = CSRFProtect()

# Política de conteúdo: só carrega scripts do próprio sistema. As fontes do Google e a consulta de CEP
# (ViaCEP, feita pelo navegador) são as únicas exceções.
POLITICA_CONTEUDO = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self' https://viacep.com.br",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


class ProvedorJSON(DefaultJSONProvider):
    """Datas em ISO 8601 sem fuso (2026-10-30T10:00:00).

    O padrão do Flask devolve 'Fri, 30 Oct 2026 10:00:00 GMT', que o navegador não consegue ler
    como horário local de Brasília e faz as telas mostrarem data errada.
    """

    @staticmethod
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat(timespec="seconds")
        if isinstance(o, date):
            return o.isoformat()
        return DefaultJSONProvider.default(o)


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)
    app.json = ProvedorJSON(app)
    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "troque-por-uma-chave-longa-e-aleatoria":
        if not app.config.get("TESTING"):
            raise RuntimeError("Configure FLASK_SECRET_KEY no arquivo .env antes de iniciar o sistema.")
    if app.config.get("DB_PASSWORD") is None:
        raise RuntimeError("Configure DB_PASSWORD no arquivo .env.")
    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    csrf.init_app(app)
    if not app.config.get("TESTING"):
        try:
            inicializar_pool(app)
        except Exception as exc:
            app.logger.error("A conexão com MySQL será inicializada na primeira consulta: %s", exc)
    app.teardown_appcontext(fechar_conexao)
    registrar_rotas(app)
    registrar_erros(app)
    _configurar_log(app)
    _registrar_controles(app)
    return app


def _configurar_log(app):
    log_path = app.config.get("LOG_FILE", "logs/estacionamento.log")
    app.logger.setLevel(logging.INFO)
    try:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        app.logger.addHandler(handler)
    except OSError:
        app.logger.warning("Não foi possível criar o arquivo de log configurado.")


def _registrar_controles(app):
    @app.before_request
    def controlar_sessao():
        if not session.get("usuario_id") or request.endpoint == "static":
            return None
        if app.config.get("REVALIDAR_SESSAO", True) and not app.config.get("TESTING"):
            if not revalidar_sessao():
                if request.path.startswith("/api/"):
                    raise ErroNegocio("Sua sessão foi encerrada. Entre novamente.", 401)
                return redirect("/login")
        session.permanent = True
        session.modified = True
        liberadas = ("/api/trocar-senha", "/api/csrf", "/trocar-senha", "/api/logout")
        if session.get("trocar_senha") and request.path not in liberadas and request.path.startswith("/api/"):
            raise ErroNegocio("Troque sua senha antes de continuar.", 403)
        return None

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        resposta.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        resposta.headers.setdefault("Content-Security-Policy", POLITICA_CONTEUDO)
        if app.config.get("SESSION_COOKIE_SECURE"):
            resposta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.endpoint != "static":
            # Telas e dados do sistema nunca ficam guardados no navegador: ao sair, o botão "voltar"
            # não reabre uma página interna a partir do histórico.
            resposta.headers["Cache-Control"] = "no-store, max-age=0"
            resposta.headers["Pragma"] = "no-cache"
        return resposta
