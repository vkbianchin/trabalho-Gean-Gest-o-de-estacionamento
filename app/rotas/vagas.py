from flask import Blueprint, jsonify, request
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import crud, cadastros, manutencao
bp=Blueprint("vagas",__name__)
@bp.get("/api/vagas")
@exigir("cadastros")
def vagas(): return jsonify(crud.listar("vagas"))

@bp.post("/api/vagas")
@exigir("cadastros")
def criar_vaga(): return jsonify({"id":cadastros.criar_vaga(request.get_json(force=True),exigir_login())}),201

@bp.put("/api/vagas/<int:vid>")
@exigir("estrutura")
def editar_vaga(vid): return jsonify(manutencao.editar_vaga(vid, request.get_json(force=True), exigir_login()))

@bp.post("/api/vagas/<int:vid>/ativo")
@exigir("estrutura")
def situacao_vaga(vid): return jsonify(manutencao.alterar_situacao_vaga(vid, bool(request.get_json(force=True).get("ativo")), exigir_login()))
