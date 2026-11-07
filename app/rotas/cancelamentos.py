from flask import Blueprint, jsonify, request

from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import cancelamentos

bp = Blueprint("cancelamentos", __name__)


@bp.post("/api/movimentacoes/<int:movimentacao_id>/cancelar")
@exigir("cancelar")
def cancelar_movimentacao(movimentacao_id):
    d = request.get_json(force=True)
    return jsonify(cancelamentos.cancelar_movimentacao(movimentacao_id, d.get("motivo"), exigir_login()))


@bp.post("/api/pagamentos/<int:pagamento_id>/cancelar")
@exigir("cancelar")
def cancelar_pagamento(pagamento_id):
    d = request.get_json(force=True)
    return jsonify(cancelamentos.cancelar_pagamento(pagamento_id, d.get("motivo"), exigir_login()))
