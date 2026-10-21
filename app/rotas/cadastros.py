from flask import Blueprint, request, jsonify, session
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import cadastros, crud
from ..erros import ErroNegocio

bp=Blueprint("cadastros",__name__)

@bp.get("/api/clientes")
@exigir("cadastros")
def clientes(): return jsonify(crud.listar("clientes"))

@bp.post("/api/clientes")
@exigir("cadastros")
def criar_cliente(): return jsonify({"id":cadastros.criar_cliente(request.get_json(force=True),exigir_login())}),201

@bp.get("/api/veiculos")
@exigir("cadastros")
def veiculos(): return jsonify(crud.listar("veiculos"))

@bp.post("/api/veiculos")
@exigir("cadastros")
def criar_veiculo(): return jsonify({"id":cadastros.criar_veiculo(request.get_json(force=True),exigir_login())}),201

@bp.get("/api/catalogos/<nome>")
@exigir("cadastros")
def catalogo(nome):
    try: return jsonify(cadastros.listar_catalogo(nome))
    except ErroNegocio: raise


@bp.post("/api/planos")
@exigir("precos")
def criar_plano():
    return jsonify({"id": cadastros.criar_plano(request.get_json(force=True), exigir_login())}), 201

@bp.put("/api/planos/<int:plano_id>")
@exigir("precos")
def editar_plano(plano_id):
    cadastros.editar_plano(plano_id, request.get_json(force=True), exigir_login())
    return jsonify({"ok": True})

@bp.post("/api/planos/<int:plano_id>/ativo")
@exigir("precos")
def alterar_situacao_plano(plano_id):
    dados = request.get_json(force=True)
    cadastros.alterar_situacao_plano(plano_id, bool(dados.get("ativo")), exigir_login())
    return jsonify({"ok": True})


@bp.get("/api/precos")
@exigir("cadastros")
def precos():
    return jsonify(cadastros.listar_precos())

@bp.post("/api/precos")
@exigir("precos")
def criar_preco():
    return jsonify({"id": cadastros.criar_preco(request.get_json(force=True), exigir_login())}), 201

@bp.put("/api/precos/<int:preco_id>")
@exigir("precos")
def editar_preco(preco_id):
    cadastros.editar_preco(preco_id, request.get_json(force=True), exigir_login())
    return jsonify({"ok": True})