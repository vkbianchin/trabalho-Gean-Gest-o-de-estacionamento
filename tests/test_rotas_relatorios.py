from datetime import date, datetime
from decimal import Decimal

import pytest

from app.servicos import financeiro, recibos, relatorios


def logar(client, nivel):
    with client.session_transaction() as sessao:
        sessao.update({"usuario_id": 1, "nome": "Teste", "login": "teste", "nivel_acesso": nivel, "trocar_senha": False})


ROTAS_ADMIN = ["/api/financeiro/resumo", "/api/financeiro/inadimplencia", "/api/financeiro/caixas",
               "/api/relatorios/movimentacoes", "/api/relatorios/movimentacoes.csv",
               "/api/relatorios/recebimentos", "/api/relatorios/recebimentos.csv", "/api/relatorios/ocupacao"]


@pytest.mark.parametrize("rota", ROTAS_ADMIN)
def test_operador_nao_acessa_financeiro_nem_relatorios(client, rota):
    logar(client, "operador")
    assert client.get(rota).status_code == 403


@pytest.mark.parametrize("rota", ROTAS_ADMIN)
def test_sem_login_as_apis_devolvem_401(client, rota):
    assert client.get(rota).status_code == 401


def test_periodo_invalido_devolve_erro_claro(client):
    logar(client, "administrador")
    r = client.get("/api/financeiro/resumo?inicio=2026-10-31&fim=2026-10-01")
    assert r.status_code == 400 and "anterior" in r.get_json()["erro"]
    assert client.get("/api/financeiro/resumo?inicio=31/10/2026&fim=2026-10-31").status_code == 400


def test_resumo_usa_o_periodo_pedido(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(financeiro, "resumo", lambda ini, fim: capturado.update(ini=ini, fim=fim) or {"total_recebido": "0.00"})
    logar(client, "administrador")
    r = client.get("/api/financeiro/resumo?inicio=2026-10-01&fim=2026-10-15")
    assert r.status_code == 200 and capturado == {"ini": date(2026, 10, 1), "fim": date(2026, 10, 15)}


def test_csv_de_movimentacoes_baixa_com_bom_e_nome_do_periodo(client, monkeypatch):
    monkeypatch.setattr(relatorios, "movimentacoes", lambda ini, fim: [
        {"id": 1, "placa": "ABC1D23", "tipo_veiculo": "Carro", "plano": "Horista", "vaga": 3, "entrada_em": datetime(2026, 10, 30, 10, 0),
         "saida_em": datetime(2026, 10, 30, 12, 35), "tempo": "2h 35min", "valor": Decimal("36"), "operador": "=HYPERLINK(\"x\")"}])
    logar(client, "administrador")
    r = client.get("/api/relatorios/movimentacoes.csv?inicio=2026-10-01&fim=2026-10-31")
    assert r.status_code == 200 and r.mimetype == "text/csv"
    assert "movimentacoes_2026-10-01_a_2026-10-31.csv" in r.headers["Content-Disposition"]
    corpo = r.get_data(as_text=True)
    assert corpo.startswith("\ufeff") and "30/10/2026 12:35" in corpo and "36,00" in corpo
    assert "'=HYPERLINK" in corpo  # fórmula neutralizada


# ---- recibo ------------------------------------------------------------------------
RECIBO = {"numero": 5, "estabelecimento": {"nome": "Central", "cnpj": None, "endereco": None, "telefone": None}, "mensalidade": False,
          "cliente": "Cliente horista", "documento": None, "placa": "ABC1D23", "competencia": None, "vaga": 3,
          "entrada_em": datetime(2026, 10, 30, 10, 0), "saida_em": datetime(2026, 10, 30, 12, 35), "permanencia": "2h 35min",
          "valor": Decimal("36.00"), "forma": "Pix", "pago_em": datetime(2026, 10, 30, 12, 35), "atendente": "Ana"}


def test_recibo_exige_login(client):
    r = client.get("/recibo/pagamento/5")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_recibo_mostra_valor_permanencia_e_repassa_documento(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(recibos, "montar_recibo", lambda pid, doc: capturado.update(pid=pid, doc=doc) or RECIBO)
    logar(client, "operador")
    r = client.get("/recibo/pagamento/5?documento=11222333000181")
    corpo = r.get_data(as_text=True)
    assert r.status_code == 200 and capturado == {"pid": 5, "doc": "11222333000181"}
    assert "Recibo de pagamento nº 5" in corpo and "R$ 36,00" in corpo and "2h 35min" in corpo and "sem valor fiscal" in corpo


def test_recibo_recusa_documento_invalido():
    class Cur:
        def execute(self, *a): pass
        def fetchone(self): return {"id": 1, "valor": Decimal("5"), "situacao": "pago", "cliente_documento": None, "entrada_em": None, "saida_em": None,
                                     "forma_pagamento": "pix", "pago_em": None, "competencia": None, "contrato_id": None, "placa_contrato": None,
                                     "placa_mov": "ABC1D23", "vaga_numero": 1, "cliente_nome": None, "atendente": None}
        def close(self): pass
    class Conn:
        def cursor(self, **_): return Cur()
    import app.servicos.recibos as mod
    mod.conexao = lambda: Conn()
    mod.configuracoes.obter = lambda: {"nome_estacionamento": "X"}
    from app.erros import ErroNegocio
    with pytest.raises(ErroNegocio, match="CPF"):
        mod.montar_recibo(1, "123")
    dados = mod.montar_recibo(1, "529.982.247-25")
    assert dados["documento"] == "529.982.247-25" and dados["cliente"] == "Cliente horista"
