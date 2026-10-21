from flask import Blueprint, request, jsonify
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import pagamentos, crud
bp=Blueprint("pagamentos",__name__)
@bp.get("/api/pagamentos")
@exigir("operacao")
def listar(): return jsonify(crud.listar("pagamentos"))
@bp.post("/api/pagamentos/<int:pagamento_id>/receber")
@exigir("operacao")
def receber(pagamento_id):
    d=request.get_json(force=True); return jsonify(pagamentos.receber_mensalidade(pagamento_id,exigir_login(),d.get("forma_pagamento")))
@bp.post("/api/pagamentos/gerar-mensalidades")
@exigir("contratos")
def gerar(): return jsonify(pagamentos.gerar_mensalidades(exigir_login()))
