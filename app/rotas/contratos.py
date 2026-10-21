from flask import Blueprint, request, jsonify
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import contratos, crud
bp=Blueprint("contratos",__name__)
@bp.get("/api/contratos")
@exigir("contratos")
def listar(): return jsonify(crud.listar("contratos"))
@bp.post("/api/contratos")
@exigir("contratos")
def criar(): return jsonify({"id":contratos.criar(request.get_json(force=True),exigir_login())}),201
@bp.post("/api/contratos/<int:contrato_id>/encerrar")
@exigir("contratos")
def encerrar(contrato_id):
    d=request.get_json(force=True); contratos.encerrar(contrato_id,exigir_login(),d.get("data_fim"),d.get("motivo")); return jsonify({"mensagem":"Contrato encerrado."})
