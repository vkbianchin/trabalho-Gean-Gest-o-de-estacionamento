import pytest
from app import create_app
from app.config import Config


class ConfigTeste(Config):
    TESTING = True
    SECRET_KEY = "chave-somente-para-testes"


@pytest.fixture()
def app():
    return create_app(ConfigTeste)


@pytest.fixture()
def client(app):
    return app.test_client()
