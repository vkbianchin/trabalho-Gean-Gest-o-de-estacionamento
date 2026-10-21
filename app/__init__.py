import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, session
from flask_wtf.csrf import CSRFProtect
from .config import Config
from .db import fechar_conexao, inicializar_pool
from .erros import registrar_erros, ErroNegocio
from .rotas import registrar_rotas

csrf=CSRFProtect()

def create_app(config_class=Config):
    app=Flask(__name__,template_folder="../templates",static_folder="../static")
    app.config.from_object(config_class)
    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"]=="troque-por-uma-chave-longa-e-aleatoria":
        if not app.config.get("TESTING"):
            raise RuntimeError("Configure FLASK_SECRET_KEY no arquivo .env antes de iniciar o sistema.")
    if app.config.get("DB_PASSWORD") is None: raise RuntimeError("Configure DB_PASSWORD no arquivo .env.")
    csrf.init_app(app)
    if not app.config.get("TESTING"):
        try: inicializar_pool(app)
        except Exception as exc: app.logger.error("A conexão com MySQL será inicializada na primeira consulta: %s",exc)
    app.teardown_appcontext(fechar_conexao)
    registrar_rotas(app)
    registrar_erros(app)
    log_path=app.config.get("LOG_FILE","logs/estacionamento.log")
    try:
        os.makedirs(os.path.dirname(log_path) or ".",exist_ok=True)
        handler=RotatingFileHandler(log_path,maxBytes=2_000_000,backupCount=5,encoding="utf-8")
        handler.setLevel(logging.INFO); handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); app.logger.addHandler(handler)
    except OSError: app.logger.warning("Não foi possível criar o arquivo de log configurado.")
    @app.before_request
    def controlar_sessao():
        if session.get("usuario_id"):
            session.permanent=True
            session.modified=True
            if session.get("trocar_senha") and request.path not in ("/api/trocar-senha","/api/csrf","/trocar-senha","/api/logout"):
                if request.path.startswith("/api/"): raise ErroNegocio("Troque sua senha antes de continuar.",403)
    return app
