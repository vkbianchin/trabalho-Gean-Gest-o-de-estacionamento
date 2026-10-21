import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "estacionamento")
    DB_USER = os.getenv("DB_USER", "estacionamento_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    LOG_FILE = os.getenv("LOG_FILE", "logs/estacionamento.log")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=60 * 60)
    WTF_CSRF_TIME_LIMIT = 3600
