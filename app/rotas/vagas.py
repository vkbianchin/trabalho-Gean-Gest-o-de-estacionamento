from flask import Blueprint, jsonify, request
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import crud, cadastros
bp=Blueprint("vagas",__name__)
@bp.get("/api/vagas")
@exigir("cadastros")
def vagas(): return jsonify(crud.listar("vagas"))

@bp.post("/api/vagas")
@exigir("cadastros")
def criar_vaga(): return jsonify({"id":cadastros.criar_vaga(request.get_json(force=True),exigir_login())}),201
