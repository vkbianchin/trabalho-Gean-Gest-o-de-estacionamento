def test_post_sem_token_devolve_json_com_codigo_csrf(client):
    resposta = client.post("/api/logout")
    assert resposta.status_code == 400
    dados = resposta.get_json()
    assert dados["codigo"] == "csrf" and "expirou" in dados["erro"]


def test_post_com_token_valido_passa_pela_protecao(client):
    token = client.get("/api/csrf").get_json()["csrf_token"]
    resposta = client.post("/api/logout", headers={"X-CSRFToken": token})
    assert resposta.status_code == 200


def test_token_antigo_depois_de_nova_sessao_e_recusado(client):
    token = client.get("/api/csrf").get_json()["csrf_token"]
    client.delete_cookie("session")
    resposta = client.post("/api/logout", headers={"X-CSRFToken": token})
    assert resposta.status_code == 400 and resposta.get_json()["codigo"] == "csrf"
