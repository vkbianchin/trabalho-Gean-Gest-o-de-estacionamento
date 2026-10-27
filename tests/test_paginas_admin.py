import pytest
from app.permissoes import PERMISSOES
from app.rotas.paginas import PAGINAS_PERMISSAO

SO_ADMINISTRADOR = ["/contratos", "/configuracoes", "/usuarios", "/auditoria"]
LIBERADAS_PARA_OPERADOR = ["/", "/caixa", "/movimentacoes", "/clientes", "/veiculos", "/catalogos", "/vagas", "/pagamentos"]


def logar(client, nivel):
    with client.session_transaction() as sessao:
        sessao.update({"usuario_id": 1, "nome": "Teste", "login": "teste", "nivel_acesso": nivel, "trocar_senha": False})


@pytest.mark.parametrize("rota", SO_ADMINISTRADOR)
def test_operador_nao_abre_pagina_de_administrador(client, rota):
    logar(client, "operador")
    assert client.get(rota).status_code == 403


@pytest.mark.parametrize("rota", SO_ADMINISTRADOR)
def test_administrador_abre_pagina_de_administrador(client, rota):
    logar(client, "administrador")
    assert client.get(rota).status_code == 200


@pytest.mark.parametrize("rota", LIBERADAS_PARA_OPERADOR)
def test_operador_continua_abrindo_paginas_de_operacao(client, rota):
    logar(client, "operador")
    assert client.get(rota).status_code == 200


@pytest.mark.parametrize("rota", SO_ADMINISTRADOR)
def test_sem_login_redireciona_para_login(client, rota):
    resposta = client.get(rota)
    assert resposta.status_code == 302 and "/login" in resposta.headers["Location"]


def test_paginas_restritas_seguem_a_tabela_de_permissoes_das_apis():
    assert set(PAGINAS_PERMISSAO) == set(SO_ADMINISTRADOR)
    for permissao in PAGINAS_PERMISSAO.values():
        assert "operador" not in PERMISSOES[permissao]
