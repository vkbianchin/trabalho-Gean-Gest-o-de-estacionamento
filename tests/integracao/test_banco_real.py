"""Testes contra um MariaDB de verdade: exercitam o SQL que os testes unitários não alcançam.

Só rodam com PARKFLOW_TESTE_BANCO=1 e as variáveis DB_HOST/DB_PORT/DB_USER/DB_PASSWORD apontando para
um servidor DESCARTÁVEL: o banco DB_NAME é APAGADO e recriado a partir de banco/schema.sql.
No GitHub Actions isso já está configurado (veja .github/workflows/ci.yml). Localmente:

    PARKFLOW_TESTE_BANCO=1 DB_NAME=parkflow_teste DB_USER=root DB_PASSWORD=... python -m pytest tests/integracao -v

Os testes seguem uma ordem (cada um usa o que o anterior deixou no banco).
"""
import os
import re
from datetime import timedelta
from pathlib import Path

import mysql.connector
import pytest

if not os.getenv("PARKFLOW_TESTE_BANCO"):
    pytest.skip("defina PARKFLOW_TESTE_BANCO=1 (e DB_*) para rodar os testes com banco real", allow_module_level=True)

from app import create_app, totp
from app.db import conexao
from app.erros import ErroNegocio
from app.servicos import (cadastros, cancelamentos, caixa, contratos, financeiro, manutencao, movimentacoes,
                          pagamentos, recibos, relatorios, usuarios)
from app.tempo import agora, hoje
from tests.conftest import ConfigTeste

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
PARAMETROS = dict(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")),
                  user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""))
NOME_BANCO = os.getenv("DB_NAME", "parkflow_teste")


class ConfigBanco(ConfigTeste):
    DB_HOST, DB_PORT = PARAMETROS["host"], PARAMETROS["port"]
    DB_USER, DB_PASSWORD, DB_NAME = PARAMETROS["user"], PARAMETROS["password"], NOME_BANCO
    DB_POOL_SIZE = 3


def comandos_do_schema():
    """Quebra banco/schema.sql em comandos (remove comentários `--` e separa por `;`)."""
    texto = re.sub(r"--.*$", "", (RAIZ / "banco" / "schema.sql").read_text(encoding="utf-8"), flags=re.M)
    return [c.strip() for c in texto.split(";") if c.strip()]


def recriar_banco():
    admin = mysql.connector.connect(**PARAMETROS)
    cur = admin.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS `{NOME_BANCO}`")
    cur.execute(f"CREATE DATABASE `{NOME_BANCO}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{NOME_BANCO}`")
    for comando in comandos_do_schema():  # um erro de SQL aqui aponta exatamente o trecho problemático do schema
        cur.execute(comando)
    admin.commit()
    cur.close()
    admin.close()


def sql(comando, params=()):
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    cur.execute(comando, params)
    linhas = cur.fetchall() if cur.with_rows else []
    conn.commit()
    cur.close()
    return linhas


@pytest.fixture(scope="module")
def mundo():
    recriar_banco()
    app = create_app(ConfigBanco)
    with app.test_request_context():
        m = {}
        m["adm"] = usuarios.criar_usuario("Admin Teste", "admin@teste.com", "admin", "Senha1234", "administrador", None, False)
        m["op"] = usuarios.criar_usuario("Operadora Teste", "op@teste.com", "operadora", "Senha1234", "operador", m["adm"], False)
        sql("INSERT INTO configuracoes (id, nome_estacionamento, tolerancia_minutos, arredondamento, fracao_minutos) VALUES (1,'Central',10,'fracao',30)")
        sql("INSERT INTO tipos_veiculo (nome) VALUES ('Carro'),('Moto')")
        m["carro"], m["moto"] = (sql("SELECT id FROM tipos_veiculo WHERE nome=%s", (n,))[0]["id"] for n in ("Carro", "Moto"))
        m["horista"] = cadastros.criar_plano({"nome": "Horista", "cobranca": "hora"}, m["adm"])
        m["mensal"] = cadastros.criar_plano({"nome": "Mensalista", "cobranca": "mensal"}, m["adm"])
        cadastros.criar_preco({"plano_id": m["horista"], "tipo_veiculo_id": m["carro"], "valor": "12.00"}, m["adm"])
        for numero, tipo, plano in ((1, m["carro"], m["horista"]), (2, m["carro"], m["horista"]), (3, m["moto"], m["horista"]), (4, m["carro"], m["mensal"])):
            cadastros.criar_vaga({"numero": numero, "tipo_veiculo_id": tipo, "plano_id": plano}, m["adm"])
        base = {"telefone": "(49) 99999-0000", "cep": "89560-000", "logradouro": "Rua A", "numero": "10", "bairro": "Centro", "cidade": "Videira", "uf": "SC"}
        m["pf"] = cadastros.criar_cliente({**base, "nome": "Maria Souza", "documento": "529.982.247-25"}, m["adm"])
        m["pj"] = cadastros.criar_cliente({**base, "nome": "Oficina Central Ltda", "tipo_pessoa": "juridica", "documento": "11.222.333/0001-81"}, m["adm"])
        m["veiculo"] = cadastros.criar_veiculo({"placa": "MEN5A55", "cliente_id": m["pf"], "tipo_veiculo_id": m["carro"]}, m["adm"])
        yield m


def entrada(mundo, placa, minutos_atras=0):
    r = movimentacoes.registrar_entrada(placa, mundo["carro"], mundo["adm"])
    if minutos_atras:
        sql("UPDATE movimentacoes SET entrada_em=%s WHERE placa=%s AND aberta=1", (agora() - timedelta(minutes=minutos_atras), placa))
    return r


def test_schema_tem_as_colunas_que_o_codigo_usa(mundo):
    esperadas = {("clientes", "documento"), ("clientes", "tipo_pessoa"), ("configuracoes", "dias_carencia_atraso"), ("movimentacoes", "cancelada"),
                 ("movimentacoes", "aberta"), ("pagamentos", "cancelado_por"), ("usuarios", "totp_ativo"), ("usuarios", "preferencias")}
    achadas = {(r["table_name"], r["column_name"]) for r in sql(
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema=DATABASE()")}
    assert esperadas <= achadas, esperadas - achadas


def test_abrir_caixa(mundo):
    caixa.abrir(mundo["adm"], "50.00")
    mundo["caixa"] = caixa.caixa_aberto(mundo["adm"])["id"]
    assert mundo["caixa"]


def test_entrada_duplicada_e_recusada(mundo):
    entrada(mundo, "DUP1D11")
    with pytest.raises(ErroNegocio):
        movimentacoes.registrar_entrada("DUP1D11", mundo["carro"], mundo["adm"])
    cancelamentos.cancelar_movimentacao(sql("SELECT id FROM movimentacoes WHERE placa='DUP1D11'")[0]["id"], "Teste de duplicidade", mundo["adm"])


def test_saida_com_cobranca_historico_e_recibo(mundo):
    entrada(mundo, "ABC1D23", minutos_atras=155)
    previa = movimentacoes.previa_saida("ABC1D23")
    assert previa["tempo"] == "2h 35min" and previa["valor"] == "30.00" and previa["exige_pagamento"]
    saida = movimentacoes.registrar_saida("ABC1D23", mundo["adm"], mundo["caixa"], "pix")
    mundo["pagamento"] = saida["pagamento_id"]
    assert saida["pagamento_id"] and saida["valor"] == "30.00"
    recibo = recibos.montar_recibo(saida["pagamento_id"], "529.982.247-25")
    assert str(recibo["valor"]) == "30.00" and recibo["placa"] == "ABC1D23" and recibo["documento"] == "529.982.247-25"
    h = movimentacoes.historico_placa("ABC1D23")
    assert h["totais"]["visitas"] == 1 and h["totais"]["total_gasto"] == "30.00"


def test_financeiro_e_relatorios(mundo):
    r = financeiro.resumo(hoje(), hoje())
    assert r["total_recebido"] == "30.00" and r["por_forma"][0]["forma_pagamento"] == "pix" and r["saidas"] >= 1
    assert any(m["placa"] == "ABC1D23" for m in relatorios.movimentacoes(hoje(), hoje()))
    assert not any(m["placa"] == "DUP1D11" for m in relatorios.movimentacoes(hoje(), hoje()))  # cancelada fica de fora
    assert relatorios.recebimentos(hoje(), hoje())[0]["origem"] == "Horista"
    assert relatorios.ocupacao(hoje(), hoje())["total_entradas"] >= 1
    assert len(financeiro.caixas_do_periodo(hoje(), hoje())) == 1


def test_estorno_de_pagamento_horista(mundo):
    r = cancelamentos.cancelar_pagamento(mundo["pagamento"], "Cobrança em duplicidade", mundo["adm"])
    assert r["situacao"] == "cancelado"
    assert financeiro.resumo(hoje(), hoje())["total_recebido"] == "0.00"
    with pytest.raises(ErroNegocio):
        cancelamentos.cancelar_pagamento(mundo["pagamento"], "Outra tentativa", mundo["adm"])


def test_cancelar_entrada_libera_a_vaga(mundo):
    entrada(mundo, "CAN1C11")
    assert movimentacoes.consultar_placa("CAN1C11")["movimentacao_aberta"]
    cancelamentos.cancelar_movimentacao(sql("SELECT id FROM movimentacoes WHERE placa='CAN1C11'")[0]["id"], "Placa digitada errada", mundo["adm"])
    assert movimentacoes.consultar_placa("CAN1C11")["movimentacao_aberta"] is None
    entrada(mundo, "CAN1C11")  # a placa e a vaga voltam a ficar livres
    cancelamentos.cancelar_movimentacao(sql("SELECT id FROM movimentacoes WHERE placa='CAN1C11' AND cancelada=0")[0]["id"], "Limpeza do teste", mundo["adm"])


def test_mensalista_atraso_recebimento_e_estorno(mundo):
    mundo["contrato"] = contratos.criar({"cliente_id": mundo["pf"], "veiculo_id": mundo["veiculo"], "valor_mensal": "300.00",
                                         "dia_vencimento": 5, "data_inicio": "2026-01-01"}, mundo["adm"])
    pagamentos.gerar_mensalidades(mundo["adm"])
    consulta = movimentacoes.consultar_placa("MEN5A55")
    assert consulta["mensalista"] and consulta["mensalista"]["em_atraso"]["quantidade"] >= 1
    assert financeiro.inadimplencia()
    primeira = sql("SELECT id FROM pagamentos WHERE contrato_id=%s AND situacao='aberto' ORDER BY vencimento LIMIT 1", (mundo["contrato"],))[0]["id"]
    pagamentos.receber_mensalidade(primeira, mundo["adm"], "dinheiro")
    assert sql("SELECT situacao FROM pagamentos WHERE id=%s", (primeira,))[0]["situacao"] == "pago"
    assert cancelamentos.cancelar_pagamento(primeira, "Pago na parcela errada", mundo["adm"])["situacao"] == "aberto"


def test_manutencao_de_cadastros(mundo):
    manutencao.editar_cliente(mundo["pf"], {"nome": "Maria Souza", "telefone": "(49) 98888-7777", "cep": "89560-000", "logradouro": "Rua A",
                                            "numero": "10", "bairro": "Centro", "cidade": "Joaçaba", "uf": "SC"}, mundo["adm"])
    assert sql("SELECT telefone, cidade FROM clientes WHERE id=%s", (mundo["pf"],))[0] == {"telefone": "49988887777", "cidade": "Joaçaba"}
    with pytest.raises(ErroNegocio):  # tem contrato vigente
        manutencao.alterar_situacao_cliente(mundo["pf"], False, mundo["adm"])
    with pytest.raises(ErroNegocio):  # veículo com contrato vigente
        manutencao.alterar_situacao_veiculo(mundo["veiculo"], False, mundo["adm"])
    entrada(mundo, "OCU1P11")
    vaga = sql("SELECT vaga_id FROM movimentacoes WHERE placa='OCU1P11' AND aberta=1")[0]["vaga_id"]
    with pytest.raises(ErroNegocio):  # vaga ocupada
        manutencao.alterar_situacao_vaga(vaga, False, mundo["adm"])
    cancelamentos.cancelar_movimentacao(sql("SELECT id FROM movimentacoes WHERE placa='OCU1P11'")[0]["id"], "Limpeza do teste", mundo["adm"])
    manutencao.alterar_situacao_vaga(vaga, False, mundo["adm"])
    assert sql("SELECT ativo FROM vagas WHERE id=%s", (vaga,))[0]["ativo"] == 0


def test_senha_provisoria_preferencias_e_dois_fatores(mundo):
    reset = usuarios.redefinir_senha_admin(mundo["op"], mundo["adm"])
    sessao = usuarios.login("operadora", reset["senha_provisoria"])
    assert sessao["trocar_senha"] is True
    assert usuarios.salvar_preferencias(mundo["adm"], {"tema": "claro", "tamanho_texto": "normal", "cor_destaque": "verde", "sons": "ligados"})
    dados = usuarios.iniciar_2fa(mundo["adm"], "admin")
    usuarios.confirmar_2fa(mundo["adm"], totp.codigo_em(dados["segredo"]))
    assert usuarios.login("admin", "Senha1234") == {"exige_2fa": True}
    final = usuarios.login_segundo_fator(totp.codigo_em(dados["segredo"]))
    assert final["login"] == "admin"
    from flask import session
    assert session["preferencias"]["tema"] == "claro"
