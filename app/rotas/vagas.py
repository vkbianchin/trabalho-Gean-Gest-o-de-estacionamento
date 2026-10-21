from flask import Blueprint, jsonify
from ..permissoes import exigir
from ..servicos import crud
bp=Blueprint("vagas",__name__)
@bp.get("/api/vagas")
@exigir("cadastros")
def vagas(): return jsonify(crud.listar("vagas"))
