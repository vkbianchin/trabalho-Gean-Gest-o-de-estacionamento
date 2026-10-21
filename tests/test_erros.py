from app.erros import ErroNegocio

def test_erro_negocio_guarda_status():
    erro=ErroNegocio("Teste",403)
    assert erro.mensagem=="Teste" and erro.status==403
