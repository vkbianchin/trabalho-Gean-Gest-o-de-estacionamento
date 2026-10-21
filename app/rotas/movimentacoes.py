from flask import Blueprint, request, jsonify
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import movimentacoes, crud
from ..erros import ErroNegocio
bp=Blueprint("movimentacoes",__name__)
@bp.get("/api/placa/<valor_placa>")
@exigir("operacao")
def placa(valor_placa): return jsonify(movimentacoes.consultar_placa(valor_placa))
@bp.get("/api/movimentacoes")
@exigir("operacao")
def listar(): return jsonify(crud.listar("movimentacoes"))
@bp.post("/api/entrada")
@exigir("operacao")
def entrada():
    d=request.get_json(force=True)
    if d.get("retroativa"): raise ErroNegocio("Entradas retroativas devem ser implementadas em rota exclusiva de administrador.",403)
    return jsonify(movimentacoes.registrar_entrada(d.get("placa"),d.get("tipo_veiculo_id"),exigir_login(),d.get("vaga_id"))),201
@bp.post("/api/saida")
@exigir("operacao")
def saida():
    d=request.get_json(force=True)
    if d.get("retroativa"): raise ErroNegocio("Saídas retroativas devem ser implementadas em rota exclusiva de administrador.",403)
    return jsonify(movimentacoes.registrar_saida(d.get("placa"),exigir_login(),d.get("caixa_id"),d.get("forma_pagamento"))),200
